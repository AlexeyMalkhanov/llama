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

import com.cloudera.llama.am.api.LlamaAM;
import com.cloudera.llama.am.api.LlamaAMException;
import com.cloudera.llama.util.FastFormat;
import com.cloudera.llama.server.ClientNotificationService;
import com.cloudera.llama.server.ClientPrincipalTProcessor;
import com.cloudera.llama.server.TypeUtils;
import com.cloudera.llama.thrift.LlamaAMAdminService;
import com.cloudera.llama.thrift.TLlamaAMAdminReleaseRequest;
import com.cloudera.llama.thrift.TLlamaAMAdminReleaseResponse;
import com.cloudera.llama.util.UUID;
import org.apache.thrift.TException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;

public class LlamaAMAdminServiceImpl implements LlamaAMAdminService.Iface {
  private static final Logger LOG = LoggerFactory.getLogger(
      LlamaAMAdminServiceImpl.class);

  private final LlamaAM llamaAM;
  private final ClientNotificationService clientNotificationService;

  public LlamaAMAdminServiceImpl(LlamaAM llamaAM,
      ClientNotificationService clientNotificationService) {
    this.llamaAM = llamaAM;
    this.clientNotificationService = clientNotificationService;
  }

  @Override
  public TLlamaAMAdminReleaseResponse Release(
      TLlamaAMAdminReleaseRequest request) throws TException {
    List<String> msgs = new ArrayList<String>();
    if (request.isSetQueues()) {
      for (String queue : request.getQueues()) {
        LOG.warn("Admin '{}' release queue '{}'",
            ClientPrincipalTProcessor.getPrincipal(), queue);
        try {
          llamaAM.releaseReservationsForQueue(queue);
        } catch (LlamaAMException ex) {
          String msg = FastFormat.format(
              "Could not release queue '{}', error: {}", queue, ex.toString());
          msgs.add(msg);
          LOG.warn(msg, ex);
        }
      }
    }
    if (request.isSetReservations()) {
      for (UUID reservation : TypeUtils.toUUIDs(request.getReservations())) {
        try {
          LOG.warn("Admin '{}' release reservation '{}'",
              ClientPrincipalTProcessor.getPrincipal(), reservation);
          llamaAM.releaseReservation(LlamaAM.ADMIN_HANDLE, reservation);
        } catch (LlamaAMException ex) {
          String msg = FastFormat.format(
              "Could not release reservation '{}', error: {}", reservation,
              ex.toString());
          msgs.add(msg);
          LOG.warn(msg, ex);
        }
      }
    }
    if (request.isSetHandles()) {
      for (UUID handle : TypeUtils.toUUIDs(request.getHandles())) {
        try {
          LOG.warn("Admin '{}' release handle '{}'",
              ClientPrincipalTProcessor.getPrincipal(), handle);
          llamaAM.releaseReservationsForHandle(handle);
          clientNotificationService.unregister(handle);
        } catch (LlamaAMException ex) {
          String msg = FastFormat.format(
              "Could not release handle '{}', error: {}", handle, ex.toString());
          msgs.add(msg);
          LOG.warn(msg, ex);
        }
      }
    }
    TLlamaAMAdminReleaseResponse resp = new TLlamaAMAdminReleaseResponse();
    resp.setStatus(TypeUtils.okWithMsgs(msgs));
    return resp;
  }

}
