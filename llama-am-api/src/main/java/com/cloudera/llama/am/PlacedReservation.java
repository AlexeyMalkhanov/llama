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
package com.cloudera.llama.am;

import com.cloudera.llama.am.impl.FastFormat;

import java.util.UUID;

public abstract class PlacedReservation extends Reservation<PlacedResource> {

  public enum Status {
    PENDING, PARTIAL, ALLOCATED
  }

  protected PlacedReservation(Reservation<Resource> reservation) {
    super(reservation);
  }

  public abstract UUID getReservationId();

  public abstract Status getStatus();

  private static final String TO_STRING_MSG = "placedReservation[clientId: {}" + 
      " queue: {} resources: {} gang: {} reservationId: {} status: {}]";

  @Override
  public String toString() {
    return FastFormat.format(TO_STRING_MSG, getClientId(), getQueue(), 
        getResources(), isGang(), getReservationId(), getStatus());
  }

  @Override
  public int hashCode() {
    return getReservationId().hashCode();
  }

  @Override
  public boolean equals(Object obj) {
    return (obj != null) && (obj instanceof PlacedReservation) &&
        getReservationId().equals(((PlacedReservation) obj).getReservationId());
  }

}
