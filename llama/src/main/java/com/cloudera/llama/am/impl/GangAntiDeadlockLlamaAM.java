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
package com.cloudera.llama.am.impl;

import com.cloudera.llama.am.api.LlamaAM;
import com.cloudera.llama.am.api.LlamaAMEvent;
import com.cloudera.llama.am.api.LlamaAMException;
import com.cloudera.llama.am.api.LlamaAMListener;
import com.cloudera.llama.am.api.PlacedReservation;
import com.cloudera.llama.am.api.PlacedResource;
import com.cloudera.llama.am.api.Reservation;
import com.cloudera.llama.server.MetricUtil;
import com.cloudera.llama.util.UUID;
import com.codahale.metrics.MetricRegistry;
import org.apache.hadoop.conf.Configuration;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.concurrent.DelayQueue;
import java.util.concurrent.Delayed;
import java.util.concurrent.TimeUnit;

public class GangAntiDeadlockLlamaAM extends LlamaAMImpl implements
    LlamaAMListener, Runnable {

  private static final String METRIC_PREFIX = LlamaAM.METRIC_PREFIX +
      "gang-anti-deadlock.";

  private static final String BACKED_OFF_RESERVATIONS_METER = METRIC_PREFIX +
      "backed-off-reservations.meter";
  private static final String BACKED_OFF_RESOURCES_METER = METRIC_PREFIX +
      "backed-off-resources.meter";

  public static final List<String> METRIC_KEYS = Arrays.asList(
      BACKED_OFF_RESERVATIONS_METER, BACKED_OFF_RESOURCES_METER);

  static class BackedOffReservation implements Delayed {
    private PlacedReservation reservation;
    private long delayedUntil;

    public BackedOffReservation(PlacedReservation reservation, long delay) {
      this.reservation = reservation;
      this.delayedUntil = System.currentTimeMillis() + delay;
    }

    public PlacedReservation getReservation() {
      return reservation;
    }

    @Override
    public long getDelay(TimeUnit unit) {
      return unit.convert(delayedUntil - System.currentTimeMillis(),
          TimeUnit.MILLISECONDS);
    }

    @Override
    public int compareTo(Delayed o) {
      return (int) (delayedUntil - ((BackedOffReservation) o).delayedUntil);
    }
  }

  private final LlamaAM am;

  //visible for testing
  Map<UUID, PlacedReservationImpl> localReservations;
  Set<UUID> submittedReservations;
  DelayQueue<BackedOffReservation> backedOffReservations;
  volatile long timeOfLastAllocation;

  private long noAllocationLimit;
  private int backOffPercent;
  private long backOffMinDelay;
  private long backOffMaxDelay;
  private Random random;

  public GangAntiDeadlockLlamaAM(Configuration conf, LlamaAM llamaAM) {
    super(conf);
    this.am = llamaAM;
    am.addListener(this);
  }

  @Override
  public void setMetricRegistry(MetricRegistry metricRegistry) {
    super.setMetricRegistry(metricRegistry);
    am.setMetricRegistry(metricRegistry);
    if (metricRegistry != null) {
      MetricUtil.registerMeter(metricRegistry, BACKED_OFF_RESERVATIONS_METER);
      MetricUtil.registerMeter(metricRegistry, BACKED_OFF_RESOURCES_METER);
    }
  }

  @Override
  public void start() throws LlamaAMException {
    am.start();
    localReservations = new HashMap<UUID, PlacedReservationImpl>();
    submittedReservations = new HashSet<UUID>();
    backedOffReservations = new DelayQueue<BackedOffReservation>();
    noAllocationLimit = getConf().getLong(
        GANG_ANTI_DEADLOCK_NO_ALLOCATION_LIMIT_KEY,
        GANG_ANTI_DEADLOCK_NO_ALLOCATION_LIMIT_DEFAULT);
    backOffPercent = getConf().getInt(
        GANG_ANTI_DEADLOCK_BACKOFF_PERCENT_KEY,
        GANG_ANTI_DEADLOCK_BACKOFF_PERCENT_DEFAULT);
    backOffMinDelay = getConf().getLong(
        GANG_ANTI_DEADLOCK_BACKOFF_MIN_DELAY_KEY,
        GANG_ANTI_DEADLOCK_BACKOFF_MIN_DELAY_DEFAULT);
    backOffMaxDelay = getConf().getLong(
        GANG_ANTI_DEADLOCK_BACKOFF_MAX_DELAY_KEY,
        GANG_ANTI_DEADLOCK_BACKOFF_MAX_DELAY_DEFAULT);
    random = new Random();
    timeOfLastAllocation = System.currentTimeMillis();
    startDeadlockResolverThread();
    am.addListener(this);
    getLog().info("Gang scheduling anti-deadlock enabled, no allocation " +
        "limit {}ms, resources backoff {}%", noAllocationLimit,
        backOffPercent);
  }

  //visible for testing
  void startDeadlockResolverThread() {
    Thread deadlockResolverThread = new Thread(this);
    deadlockResolverThread.setDaemon(true);
    deadlockResolverThread.setName("GangAntiDeadlockLlamaAM");
    deadlockResolverThread.start();
  }

  @Override
  public void stop() {
    am.stop();
  }

  @Override
  public boolean isRunning() {
    return am.isRunning();
  }

  @Override
  public List<String> getNodes() throws LlamaAMException {
    return am.getNodes();
  }

  @Override
  public void reserve(UUID reservationId, Reservation reservation)
      throws LlamaAMException {
    if (reservation.isGang()) {
      PlacedReservationImpl placedReservation =
          new PlacedReservationImpl(reservationId, reservation);
      gReserve(reservationId, placedReservation);
      reservation = placedReservation;
    }
    am.reserve(reservationId, reservation);
  }

  private synchronized void gReserve(UUID reservationId,
      PlacedReservationImpl placedReservation) {
    localReservations.put(reservationId, placedReservation);
    if (backedOffReservations.isEmpty()) {
      submittedReservations.add(reservationId);
    } else {
      backedOffReservations.add(new BackedOffReservation(placedReservation,
          getBackOffDelay()));
    }
  }

  @Override
  public PlacedReservation getReservation(UUID reservationId)
      throws LlamaAMException {
    PlacedReservation pr = am.getReservation(reservationId);
    if (pr == null) {
      pr = gGetReservation(reservationId);
    }
    return pr;
  }

  private synchronized PlacedReservation gGetReservation(UUID reservationId) {
    return localReservations.get(reservationId);
  }

  @Override
  public void releaseReservation(UUID reservationId) throws LlamaAMException {
    gReleaseReservation(reservationId);
    am.releaseReservation(reservationId);
  }

  private synchronized void gReleaseReservation(UUID reservationId) {
    localReservations.remove(reservationId);
    submittedReservations.remove(reservationId);
  }

  @Override
  public List<UUID> releaseReservationsForClientId(UUID clientId)
      throws LlamaAMException {
    List<UUID> ids = am.releaseReservationsForClientId(clientId);
    ids.addAll(gReleaseReservationsForClientId(clientId));
    return new ArrayList<UUID>(new HashSet<UUID>(ids));
  }

  private synchronized List<UUID> gReleaseReservationsForClientId(
      UUID clientId) {
    List<UUID> ids = new ArrayList<UUID>();
    Iterator<PlacedReservationImpl> it =
        localReservations.values().iterator();
    while (it.hasNext()) {
      PlacedReservation pr = it.next();
      if (pr.getClientId().equals(clientId)) {
        it.remove();
        submittedReservations.remove(pr.getReservationId());
        ids.add(pr.getReservationId());
      }
    }
    return ids;
  }

  @Override
  public void addListener(LlamaAMListener listener) {
    am.addListener(listener);
  }

  @Override
  public void removeListener(LlamaAMListener listener) {
    am.removeListener(listener);
  }

  @Override
  public synchronized void handle(LlamaAMEvent event) {
    LlamaAMEventImpl eventImpl = (LlamaAMEventImpl) event;
    for (PlacedResource resource : eventImpl.getAllocatedGangResources()) {
      if (submittedReservations.contains(resource.getReservationId())) {
        timeOfLastAllocation = System.currentTimeMillis();
        getLog().debug("Resetting last resource allocation");
        break;
      }
    }
    for (UUID id : event.getAllocatedReservationIds()) {
      localReservations.remove(id);
      submittedReservations.remove(id);
    }
    for (UUID id : event.getRejectedReservationIds()) {
      localReservations.remove(id);
      submittedReservations.remove(id);
    }
  }

  @Override
  public void run() {
    try {
      Thread.sleep(noAllocationLimit);
    } catch (InterruptedException ex) {
      //NOP
    }
    while (isRunning()) {
      try {
        long sleepTime1 = deadlockAvoidance();
        long sleepTime2 = reReserveBackOffs();
        long sleepTime = Math.min(sleepTime1, sleepTime2);
        getLog().debug("Deadlock avoidance thread sleeping for {} ms",
            sleepTime);
        Thread.sleep(sleepTime);
      } catch (InterruptedException ex) {
        //NOP
      }
    }
  }

  long deadlockAvoidance() {
    long sleepTime;
    long timeWithoutAllocations = System.currentTimeMillis() -
        timeOfLastAllocation;
    if (timeWithoutAllocations >= noAllocationLimit) {
      doReservationsBackOff();
      sleepTime = noAllocationLimit;
    } else {
      getLog().debug("Recent allocation, {} ms ago, skipping back off",
          timeWithoutAllocations);
      sleepTime = timeWithoutAllocations;
    }
    return sleepTime;
  }

  long getBackOffDelay() {
    return backOffMinDelay + random.nextInt((int)
        (backOffMaxDelay - backOffMinDelay));
  }

  synchronized void doReservationsBackOff() {
    if (submittedReservations.isEmpty()) {
      getLog().debug("No pending gang reservations to back off");
    } else {
      getLog().debug("Starting gang reservations back off");
      int numberOfGangResources = 0;
      List<UUID> submitted = new ArrayList<UUID>(submittedReservations);
      for (UUID id : submitted) {
        PlacedReservation pr = localReservations.get(id);
        if (pr != null) {
          numberOfGangResources += pr.getResources().size();
        }
      }
      int toGetRidOff = numberOfGangResources * backOffPercent / 100;
      int gotRidOff = 0;
      while (gotRidOff < toGetRidOff && !submitted.isEmpty()) {
        int victim = random.nextInt(submitted.size());
        UUID reservationId = submitted.get(victim);
        PlacedReservationImpl reservation =
            localReservations.get(reservationId);
        if (reservation != null) {
          try {
            getLog().warn("Backing off gang reservation {} with {} resources",
                reservation.getReservationId(),
                reservation.getResources().size());
            am.releaseReservation(reservation.getReservationId());
            backedOffReservations.add(
                new BackedOffReservation(reservation, getBackOffDelay()));
            submittedReservations.remove(reservationId);
            submitted.remove(reservationId);

            MetricUtil.meter(getMetricRegistry(), BACKED_OFF_RESERVATIONS_METER,
                1);
            MetricUtil.meter(getMetricRegistry(), BACKED_OFF_RESOURCES_METER,
                reservation.getResources().size());

          } catch (LlamaAMException ex) {
            getLog().warn("Error while backing off gang reservation {}: {}",
                reservation.getReservationId(), ex.toString(), ex);
          }
          gotRidOff += reservation.getResources().size();
        }
      }
      getLog().debug("Finishing gang reservations back off");
    }
    //resetting to current last allocation to start waiting again.
    timeOfLastAllocation = System.currentTimeMillis();
  }

  synchronized long reReserveBackOffs() {
    BackedOffReservation br = backedOffReservations.poll();
    if (br != null) {
      getLog().debug("Starting re-reserving backed off gang reservations");
    } else {
      getLog().debug("No backed off gang reservation to re-reserve");
    }
    while (br != null) {
      UUID reservationId = br.getReservation().getReservationId();
      if (localReservations.containsKey(reservationId)) {
        try {
          getLog().info("Re-reserving gang reservation {}",
              br.getReservation().getReservationId());
          am.reserve(reservationId, br.getReservation());
          submittedReservations.add(reservationId);
        } catch (LlamaAMException ex) {
          localReservations.remove(reservationId);
          LlamaAMEvent event = new LlamaAMEventImpl(br.getReservation().
              getClientId());
          event.getRejectedReservationIds().add(reservationId);
          dispatch(event);
        }
      }
      br = backedOffReservations.poll();
    }
    br = backedOffReservations.peek();
    return (br != null) ? br.getDelay(TimeUnit.MILLISECONDS) : Long.MAX_VALUE;
  }
}
