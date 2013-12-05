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
import com.cloudera.llama.util.ErrorCode;
import com.cloudera.llama.util.LlamaException;
import com.cloudera.llama.am.api.LlamaAMListener;
import com.cloudera.llama.am.api.PlacedReservation;
import com.cloudera.llama.am.api.PlacedResource;
import com.cloudera.llama.am.api.RMResource;
import com.cloudera.llama.am.api.TestUtils;
import com.cloudera.llama.am.spi.RMConnector;
import com.cloudera.llama.am.spi.RMEvent;
import com.cloudera.llama.am.spi.RMListener;
import com.cloudera.llama.util.UUID;
import org.apache.hadoop.conf.Configurable;
import org.apache.hadoop.conf.Configuration;
import org.junit.Assert;
import org.junit.Test;

import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class TestMultiQueueLlamaAM {

  private static Set<String> EXPECTED = new HashSet<String>();

  static {
    EXPECTED.add("setConf");
    EXPECTED.add("setLlamaAMCallback");
    EXPECTED.add("start");
    EXPECTED.add("stop");
    EXPECTED.add("register");
    EXPECTED.add("unregister");
    EXPECTED.add("getNodes");
    EXPECTED.add("reserve");
    EXPECTED.add("release");
  }

  public static class MyRMConnector implements RMConnector,
      Configurable {
    public static RMListener callback;
    public static Set<String> methods = new HashSet<String>();

    private Configuration conf;

    public MyRMConnector() {
      methods.clear();
    }

    @Override
    public void setConf(Configuration conf) {
      methods.add("setConf");
      this.conf = conf;
    }

    @Override
    public Configuration getConf() {
      return null;
    }

    @Override
    public void setLlamaAMCallback(RMListener callback) {
      MyRMConnector.callback = callback;
      methods.add("setLlamaAMCallback");
    }

    @Override
    public void start() throws LlamaException {
      methods.add("start");
      if (conf.getBoolean("fail.start", false)) {
        throw new LlamaException(ErrorCode.TEST);
      }
    }

    @Override
    public void stop() {
      methods.add("stop");
    }

    @Override
    public void register(String queue) throws LlamaException {
      methods.add("register");
      if (conf.getBoolean("fail.register", false)) {
        throw new LlamaException(ErrorCode.TEST);
      }
    }

    @Override
    public void unregister() {
      methods.add("unregister");
    }

    @Override
    @SuppressWarnings("unchecked")
    public List<String> getNodes() throws LlamaException {
      methods.add("getNodes");
      return Collections.EMPTY_LIST;
    }

    @Override
    public void reserve(Collection<RMResource> resources)
        throws LlamaException {
      methods.add("reserve");
    }

    @Override
    public void emptyCache() throws LlamaException {
    }

    @Override
    public void release(Collection<RMResource> resources,
        boolean doNotCache)
        throws LlamaException {
      methods.add("release");
      if (conf.getBoolean("release.fail", false)) {
        throw new LlamaException(ErrorCode.TEST);
      }
    }

    @Override
    public boolean reassignResource(Object rmResourceId, UUID resourceId) {
      return false;
    }

  }

  @Test
  public void testMultiQueueDelegation() throws Exception {
    Configuration conf = new Configuration(false);
    conf.setClass(LlamaAM.RM_CONNECTOR_CLASS_KEY, MyRMConnector.class,
        RMConnector.class);
    LlamaAM am = LlamaAM.create(conf);
    try {
      am.start();
      LlamaAMListener listener = new LlamaAMListener() {
        @Override
        public void onEvent(LlamaAMEvent event) {
        }
      };
      UUID handle = UUID.randomUUID();
      UUID id = am.reserve(TestUtils.createReservation(handle, "q", 1, true));
      am.getNodes();
      am.addListener(listener);
      am.removeListener(listener);
      am.getReservation(id);
      am.releaseReservation(handle, id, false);
      am.releaseReservationsForHandle(UUID.randomUUID(), false);
      am.stop();

      Assert.assertEquals(EXPECTED, MyRMConnector.methods);
    } finally {
      am.stop();
    }
  }

  @Test(expected = LlamaException.class)
  public void testReleaseReservationForClientException() throws Exception {
    Configuration conf = new Configuration(false);
    conf.setClass(LlamaAM.RM_CONNECTOR_CLASS_KEY, MyRMConnector.class,
        RMConnector.class);
    conf.setBoolean("release.fail", true);
    LlamaAM am = LlamaAM.create(conf);
    try {
      am.start();
      UUID cId = UUID.randomUUID();
      am.reserve(TestUtils.createReservation(cId, "q", 1, true));
      am.releaseReservationsForHandle(cId, false);
    } finally {
      am.stop();
    }
  }

  @Test(expected = LlamaException.class)
  public void testReleaseReservationForClientDiffQueuesException()
      throws Exception {
    Configuration conf = new Configuration(false);
    conf.setClass(LlamaAM.RM_CONNECTOR_CLASS_KEY, MyRMConnector.class,
        RMConnector.class);
    conf.setBoolean("release.fail", true);
    LlamaAM am = LlamaAM.create(conf);
    try {
      am.start();
      UUID cId = UUID.randomUUID();
      am.reserve(TestUtils.createReservation(cId, "q1", 1, true));
      am.reserve(TestUtils.createReservation(cId, "q2", 1, true));
      am.releaseReservationsForHandle(cId, false);
    } finally {
      am.stop();
    }
  }

  @Test(expected = LlamaException.class)
  public void testStartOfDelegatedLlamaAmFail() throws Exception {
    Configuration conf = new Configuration(false);
    conf.setClass(LlamaAM.RM_CONNECTOR_CLASS_KEY, MyRMConnector.class,
        RMConnector.class);
    conf.setBoolean("fail.start", true);
    conf.set(LlamaAM.INITIAL_QUEUES_KEY, "q");
    LlamaAM am = LlamaAM.create(conf);
    am.start();
  }

  @Test(expected = LlamaException.class)
  public void testRegisterOfDelegatedLlamaAmFail() throws Exception {
    Configuration conf = new Configuration(false);
    conf.setClass(LlamaAM.RM_CONNECTOR_CLASS_KEY, MyRMConnector.class,
        RMConnector.class);
    conf.setBoolean("fail.register", true);
    conf.set(LlamaAM.INITIAL_QUEUES_KEY, "q");
    LlamaAM am = LlamaAM.create(conf);
    am.start();
  }

  @Test
  public void testGetReservationUnknown() throws Exception {
    Configuration conf = new Configuration(false);
    conf.setClass(LlamaAM.RM_CONNECTOR_CLASS_KEY, MyRMConnector.class,
        RMConnector.class);
    LlamaAM am = LlamaAM.create(conf);
    am.start();
    Assert.assertNull(am.getReservation(UUID.randomUUID()));
  }

  @Test
  public void testReleaseReservationUnknown() throws Exception {
    Configuration conf = new Configuration(false);
    conf.setClass(LlamaAM.RM_CONNECTOR_CLASS_KEY, MyRMConnector.class,
        RMConnector.class);
    LlamaAM am = LlamaAM.create(conf);
    am.start();
    am.releaseReservation(UUID.randomUUID(), UUID.randomUUID(), false);
  }

  private boolean listenerCalled;

  @Test
  public void testMultiQueueListener() throws Exception {
    Configuration conf = new Configuration(false);
    conf.setClass(LlamaAM.RM_CONNECTOR_CLASS_KEY, MyRMConnector.class,
        RMConnector.class);
    LlamaAM am = LlamaAM.create(conf);
    try {
      am.start();
      LlamaAMListener listener = new LlamaAMListener() {
        @Override
        public void onEvent(LlamaAMEvent event) {
          listenerCalled = true;
        }
      };
      UUID handle = UUID.randomUUID();
      PlacedReservation rr = am.getReservation(
          am.reserve(TestUtils.createReservation(handle,
          "q", 1, true)));
      UUID id = rr.getReservationId();
      am.getNodes();
      am.addListener(listener);
      am.getReservation(id);
      Assert.assertFalse(listenerCalled);
      MyRMConnector.callback.onEvent(Arrays.asList(RMEvent
          .createStatusChangeEvent(rr.getPlacedResources().get(0).getResourceId(),
              PlacedResource.Status.REJECTED)));
      Assert.assertTrue(listenerCalled);
      am.releaseReservation(handle, id, false);
      am.releaseReservationsForHandle(UUID.randomUUID(), false);
      am.removeListener(listener);
      listenerCalled = false;
      Assert.assertFalse(listenerCalled);
      am.stop();
    } finally {
      am.stop();
    }
  }
}
