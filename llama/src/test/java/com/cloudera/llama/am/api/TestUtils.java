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
package com.cloudera.llama.am.api;

import com.cloudera.llama.am.impl.PlacedReservationImpl;
import com.cloudera.llama.am.impl.PlacedResourceImpl;
import com.cloudera.llama.util.UUID;
import junit.framework.Assert;

import java.util.Arrays;
import java.util.List;

public class TestUtils {

  public static Resource createResource(String location,
      Resource.Locality locality, int cpus, int memory) {
    Resource.Builder b = Builders.createResourceBuilder();
    b.setLocationAsk(location);
    b.setLocalityAsk(locality);
    b.setCpuVCoresAsk(cpus);
    b.setMemoryMbsAsk(memory);
    return b.build();
  }

  public static RMResource createRMResource(String location,
      Resource.Locality locality, int cpus, int memory) {
    return createPlacedResourceImpl(location, locality, cpus, memory);
  }

  public static PlacedResource createPlacedResource(String location,
      Resource.Locality locality, int cpus, int memory) {
    return createPlacedResourceImpl(location, locality, cpus, memory);
  }

  public static PlacedResourceImpl createPlacedResourceImpl(Resource resource) {
    Reservation rr = createReservation(UUID.randomUUID(), "u", "q",
        Arrays.asList(resource), true);
    PlacedReservationImpl pr = new PlacedReservationImpl(UUID.randomUUID(), rr);
    return pr.getPlacedResourceImpls().get(0);
  }

  public static PlacedResourceImpl createPlacedResourceImpl(String location,
      Resource.Locality locality, int cpus, int memory) {
    Resource r = createResource(location, locality, cpus, memory);
    return createPlacedResourceImpl(r);
  }

  public static Resource createResource(String location) {
    Resource.Builder b = Builders.createResourceBuilder();
    b.setLocationAsk(location);
    b.setLocalityAsk(Resource.Locality.MUST);
    b.setCpuVCoresAsk(1);
    b.setMemoryMbsAsk(2);
    return b.build();
  }

  public static Reservation createReservation(UUID handle, String user,
      String queue, Resource resource, boolean gang) {
    Reservation.Builder b = Builders.createReservationBuilder();
    b.setHandle(handle);
    b.setUser(user);
    b.setQueue(queue);
    b.addResources(Arrays.asList(resource));
    b.setGang(gang);
    return b.build();
  }

  public static Reservation createReservation(UUID handle, String user,
      String queue, List<Resource> resources, boolean gang) {
    Reservation.Builder b = Builders.createReservationBuilder();
    b.setHandle(handle);
    b.setUser(user);
    b.setQueue(queue);
    b.addResources(resources);
    b.setGang(gang);
    return b.build();
  }

  public static Reservation createReservation(boolean gang) {
    Reservation.Builder b = Builders.createReservationBuilder();
    b.setHandle(UUID.randomUUID());
    b.setUser("u");
    b.setQueue("q");
    b.setResources(Arrays.asList(createResource("n1")));
    b.setGang(gang);
    return b.build();
  }

  public static Reservation createReservation(UUID handle, int resources,
      boolean gang) {
    Reservation.Builder b = Builders.createReservationBuilder();
    b.setHandle(handle);
    b.setUser("u");
    b.setQueue("q");
    for (int i = 0; i < resources; i++) {
      b.addResource(createResource("n1"));
    }
    b.setGang(gang);
    return b.build();
  }

  public static Reservation createReservation(UUID handle, String queue,
      int resources, boolean gang) {
    Reservation.Builder b = Builders.createReservationBuilder();
    b.setHandle(handle);
    b.setUser("u");
    b.setQueue(queue);
    for (int i = 0; i < resources; i++) {
      b.addResource(createResource("n1"));
    }
    b.setGang(gang);
    return b.build();
  }

  public static void assertResource(Resource r1, Resource r2) {
    Assert.assertEquals(r1.getLocationAsk(), r2.getLocationAsk());
    Assert.assertEquals(r1.getLocalityAsk(), r2.getLocalityAsk());
    Assert.assertEquals(r1.getCpuVCoresAsk(), r2.getCpuVCoresAsk());
    Assert.assertEquals(r2.getMemoryMbsAsk(), r2.getMemoryMbsAsk());

  }
}
