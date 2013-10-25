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
import com.cloudera.llama.am.impl.ParamChecker;

import java.util.ArrayList;
import java.util.List;
import com.cloudera.llama.util.UUID;

public class Reservation<T extends Resource> {
  private final UUID handle;
  private final String queue;
  private final List<T> resources;
  private final boolean gang;

  public Reservation(UUID handle, String queue,
      List<? extends Resource> resources, boolean gang) {
    this.handle = ParamChecker.notNull(handle, "handle");
    this.queue = ParamChecker.notEmpty(queue, "queue");
    this.gang = gang;
    ParamChecker.notNulls(resources, "resources");
    ParamChecker.asserts(!resources.isEmpty(), "resources cannot be empty");
    this.resources = copyResources(resources);
  }

  @SuppressWarnings("unchecked")
  protected Reservation(Reservation reservation) {
    this(reservation.getHandle(), reservation.getQueue(),
        reservation.getResources(), reservation.isGang());
  }

  @SuppressWarnings("unchecked")
  protected List<T> copyResources(List<? extends Resource> resources) {
    return new ArrayList(resources);
  }

  public UUID getHandle() {
    return handle;
  }

  public String getQueue() {
    return queue;
  }

  public List<T> getResources() {
    return resources;
  }

  public boolean isGang() {
    return gang;
  }

  private static final String TO_STRING_MSG = "reservation[handle: {} " +
      "queue: {} resources: {} gang: {}]";

  public String toString() {
    return FastFormat.format(TO_STRING_MSG, getHandle(), getQueue(),
        getResources(), isGang());
  }

}
