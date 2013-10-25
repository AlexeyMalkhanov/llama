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

import com.cloudera.llama.am.impl.FastFormat;

import com.cloudera.llama.util.UUID;

public abstract class PlacedResource extends Resource {

  public enum Status {
    PENDING, ALLOCATED, REJECTED, PREEMPTED, LOST
  }

  protected PlacedResource(Resource resource) {
    super(resource);
  }

  public abstract UUID getHandle();

  public abstract String getQueue();

  public abstract UUID getReservationId();

  public abstract String getRmResourceId();

  public abstract int getActualCpuVCores();

  public abstract int getActualMemoryMb();

  public abstract String getActualLocation();

  public abstract Status getStatus();

  private static final String TO_STRING_MSG = "placedResource[" +
      "client_resource_id: {} cpuVCores: {} memoryMb: {} askedLocation: {} " +
      "enforcement: {} handle: {} queue: {} reservationId: {} " +
      "rmResourceId: {} actualCpuVCores: {} actualMemoryMb: {} " +
      "actualLocation: {} status: {}]";

  @Override
  public String toString() {
    return FastFormat.format(TO_STRING_MSG, getClientResourceId(),
        getCpuVCores(), getMemoryMb(), getLocation(), getEnforcement(), 
        getHandle(), getQueue(), getReservationId(), getRmResourceId(),
        getActualCpuVCores(), getActualMemoryMb(), getActualLocation(), 
        getStatus());
  }

  @Override
  public int hashCode() {
    return getClientResourceId().hashCode();
  }

  @Override
  public boolean equals(Object obj) {
    return (obj != null) && (obj instanceof PlacedResource) &&
        getClientResourceId().equals(((PlacedResource) obj).getClientResourceId());
  }

}
