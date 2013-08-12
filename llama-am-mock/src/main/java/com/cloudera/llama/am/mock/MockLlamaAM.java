/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.cloudera.llama.am.mock;

import com.cloudera.llama.am.LlamaAM;
import com.cloudera.llama.am.LlamaAMException;
import com.cloudera.llama.am.PlacedReservation;
import com.cloudera.llama.am.PlacedResource;
import com.cloudera.llama.am.impl.AbstractSingleQueueLlamaAM;
import com.cloudera.llama.am.impl.FastFormat;
import com.cloudera.llama.am.impl.RMPlacedReservation;
import com.cloudera.llama.am.impl.RMPlacedResource;
import com.cloudera.llama.am.impl.RMResourceChange;

import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.concurrent.Callable;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

public class MockLlamaAM extends AbstractSingleQueueLlamaAM {
  public static final String PREFIX_KEY = LlamaAM.PREFIX_KEY + "mock.";
  public static final String EVENTS_MIN_WAIT_KEY = MockLlamaAM.PREFIX_KEY +
      "events.min.wait.ms";
  public static final String EVENTS_MAX_WAIT_KEY = MockLlamaAM.PREFIX_KEY +
      "events.max.wait.ms";
  public static final String QUEUES_KEY = MockLlamaAM.PREFIX_KEY + "queues";
  public static final String NODES_KEY = MockLlamaAM.PREFIX_KEY + "nodes";


  private static final Map<String, PlacedResource.Status> MOCK_FLAGS = new 
      HashMap<String, PlacedResource.Status>();

  static {
    MOCK_FLAGS.put(MockLlamaAMFlags.ALLOCATE, PlacedResource.Status.ALLOCATED);
    MOCK_FLAGS.put(MockLlamaAMFlags.REJECT, PlacedResource.Status.REJECTED);
    MOCK_FLAGS.put(MockLlamaAMFlags.LOSE, PlacedResource.Status.LOST);
    MOCK_FLAGS.put(MockLlamaAMFlags.PREEMPT, PlacedResource.Status.PREEMPTED);
  }

  private static final Random RANDOM = new Random();

  private PlacedResource.Status getMockResourceStatus(String location) {
    PlacedResource.Status status = null;
    for (Map.Entry<String, PlacedResource.Status> entry : MOCK_FLAGS.entrySet
        ()) {
      if (location.startsWith(entry.getKey())) {
        status = entry.getValue();
      }
    }
    if (!nodes.contains(getLocation(location))) {
      status = PlacedResource.Status.REJECTED;      
    } else if (status == null) {
      int r = RANDOM.nextInt(10);
      if (r < 1) {
        status = PlacedResource.Status.LOST;
      } else if (r < 2) {
        status = PlacedResource.Status.REJECTED;
      } else if (r < 4) {
        status = PlacedResource.Status.PREEMPTED;
      } else {
        status = PlacedResource.Status.ALLOCATED;
      }
    }
    return status;
  }

  private String getLocation(String location) {
    for (Map.Entry<String, PlacedResource.Status> entry : MOCK_FLAGS.entrySet
        ()) {
      if (location.startsWith(entry.getKey())) {
        return location.substring(entry.getKey().length());
      }
    }
    return location;
  }

  private final AtomicLong counter = new AtomicLong();
  private ScheduledExecutorService scheduler;
  private int minWait;
  private int maxWait;
  private List<String> nodes;
  
  @Override
  public void start() throws LlamaAMException {
    super.start();
    minWait = getConf().getInt(EVENTS_MIN_WAIT_KEY, 5000);
    maxWait = getConf().getInt(EVENTS_MAX_WAIT_KEY, 10000);
    nodes = Collections.unmodifiableList(Arrays.asList(getConf().
        getStrings(NODES_KEY, "n1", "n2")));
    scheduler = new ScheduledThreadPoolExecutor(1);
  }


  @Override
  protected void rmRegister(String queue) throws LlamaAMException {
    Collection<String> validQueues = getConf().
        getTrimmedStringCollection(QUEUES_KEY);
    if (!validQueues.contains(queue)) {
      throw new IllegalArgumentException(FastFormat.format("Invalid queue " +
          "'{}'", queue));
    }
  }

  @Override
  protected void rmUnregister() {
    scheduler.shutdownNow();
  }

  @Override
  protected List<String> rmGetNodes() throws LlamaAMException {
    return nodes;
  }

  @Override
  protected void rmReserve(RMPlacedReservation reservation)
      throws LlamaAMException {
    schedule(this, reservation);
  }

  @Override
  protected void rmRelease(Collection<RMPlacedResource> resources)
      throws LlamaAMException {
  }

  @Override
  protected void changesFromRM(List<RMResourceChange> changes) {
    super.changesFromRM(changes);
  }

  private class MockRMAllocator implements Callable<Void> {
    private MockLlamaAM llama;
    private PlacedResource resource;
    private PlacedResource.Status status;
    private boolean initial;
    
    public MockRMAllocator(MockLlamaAM llama, PlacedResource resource,
        PlacedResource.Status status, boolean initial) {
      this.llama = llama;
      this.resource = resource;
      this.status = status;
      this.initial = initial;
    }

    private void toAllocate() {
      RMResourceChange change = RMResourceChange.createResourceAllocation
          (resource.getClientResourceId(), "c" + counter.incrementAndGet
              (), resource.getCpuVCores(), resource.getMemoryMb(),
              getLocation(resource.getLocation()));
      llama.changesFromRM(Arrays.asList(change));      
    }
    
    private void toStatus(PlacedResource.Status status) {
      RMResourceChange change = RMResourceChange.createResourceChange(
          resource.getClientResourceId(), status);
      llama.changesFromRM(Arrays.asList(change));
      
    }
    @Override
    public Void call() throws Exception {
      switch (status) {
        case ALLOCATED:
          toAllocate();
          break;
        case REJECTED: 
          toStatus(status);
          break;
        case LOST: 
        case PREEMPTED: 
          if (initial) {
            toAllocate();

            MockRMAllocator mocker = new MockRMAllocator(llama, resource, 
                status, false);
            int delay = minWait + RANDOM.nextInt(maxWait);
            scheduler.schedule(mocker, delay, TimeUnit.MILLISECONDS);
          } else {
            toStatus(status);
          }
        break;
      }
      return null;
    }
  }

  private void schedule(MockLlamaAM allocator, PlacedReservation reservation) {
    for (PlacedResource resource : reservation.getResources()) {
      PlacedResource.Status status = getMockResourceStatus(
          resource.getLocation());
      MockRMAllocator mocker = new MockRMAllocator(allocator, resource, status, 
          true);
      int delay = minWait + RANDOM.nextInt(maxWait);
      scheduler.schedule(mocker, delay, TimeUnit.MILLISECONDS);
    }
  }

}
