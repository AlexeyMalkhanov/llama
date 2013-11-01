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
import com.cloudera.llama.am.yarn.YarnRMLlamaAMConnector;
import com.cloudera.llama.server.ClientInfo;
import com.cloudera.llama.server.ClientNotificationService;
import com.cloudera.llama.server.NodeMapper;
import com.cloudera.llama.server.Security;
import com.cloudera.llama.server.ThriftEndPoint;
import com.cloudera.llama.server.ThriftServer;
import com.cloudera.llama.thrift.LlamaAMAdminService;
import com.cloudera.llama.thrift.LlamaAMService;
import com.codahale.metrics.JmxReporter;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.jmx.JMXJsonServlet;
import org.apache.hadoop.net.NetUtils;
import org.apache.hadoop.util.ReflectionUtils;
import org.mortbay.jetty.Connector;
import org.mortbay.jetty.Server;
import org.mortbay.jetty.bio.SocketConnector;
import org.mortbay.jetty.servlet.Context;
import org.mortbay.thread.QueuedThreadPool;

import java.net.InetSocketAddress;

public class LlamaAMServer extends
    ThriftServer<LlamaAMService.Processor, LlamaAMAdminService.Processor>
    implements ClientNotificationService.Listener {
  private static final int JETTY_MAX_THREADS = 20;
  private LlamaAM llamaAm;
  private ClientNotificationService clientNotificationService;
  private NodeMapper nodeMapper;
  private String httpJmx;
  private String httpLlama;
  private RestData restData;

  public LlamaAMServer() {
    super("LlamaAM", AMServerConfiguration.class);
  }

  private JmxReporter reporter;
  private Server httpServer;

  protected void startJMX() {
    reporter = JmxReporter.forRegistry(getMetricRegistry()).build();
    reporter.start();
  }

  protected String getHttpJmxEndPoint() {
    return httpJmx;
  }

  protected String getHttpLlamaUI() {
    return httpLlama;
  }

  protected void stopJMX() {
    reporter.stop();
    reporter.close();
  }

  private void startHttpServer() {
    restData = new RestData();
    httpServer = new Server();
    QueuedThreadPool qtp = new QueuedThreadPool(JETTY_MAX_THREADS);
    qtp.setName("llama-jetty");
    qtp.setDaemon(true);
    httpServer.setThreadPool(qtp);
    String strAddress = getServerConf().getHttpAddress();
    InetSocketAddress address = NetUtils.createSocketAddr(strAddress,
        getServerConf().getHttpDefaultPort());
    Connector connector = new SocketConnector();
    connector.setHost(address.getHostName());
    connector.setPort(address.getPort());
    httpServer.setConnectors(new Connector[]{connector});

    Context context = new Context();
    context.setContextPath("");
    context.setAttribute("hadoop.conf", new Configuration());
    context.addServlet(JMXJsonServlet.class, "/jmx");
    context.addServlet(LlamaServlet.class, "/*");
    context.addServlet(Log4jLoggersServlet.class, "/loggers");
    context.setAttribute(Log4jLoggersServlet.READ_ONLY,
        getServerConf().getLoggerServletReadOnly());
    context.addServlet(LlamaJsonServlet.class, LlamaJsonServlet.BIND_PATH);
    context.setAttribute(LlamaJsonServlet.REST_DATA, restData);
    httpServer.addHandler(context);

    try {
      httpServer.start();
      httpJmx = "http://" + getHostname(connector.getHost()) + ":" +
          connector.getLocalPort() + "/jmx";
      httpLlama = "http://" + getHostname(connector.getHost()) + ":" +
          connector.getLocalPort() + "/";

      getLog().info("HTTP JSON JMX     : {}", httpJmx);
      getLog().info("HTTP Llama Web UI : {}", httpLlama);
    } catch (Throwable ex) {
      throw new RuntimeException(ex);
    }
  }

  private void stopHttpServer() {
    try {
      httpServer.stop();
    } catch (Throwable ex) {
      getLog().warn("Error shutting down HTTP server, {}", ex.toString(), ex);
    }
  }

  @Override
  protected void startService() {
    startHttpServer();
    try {
      Security.loginToHadoop(getServerConf());
      Class<? extends NodeMapper> klass = getServerConf().getNodeMappingClass();
      nodeMapper = ReflectionUtils.newInstance(klass, getConf());
      clientNotificationService = new ClientNotificationService(getServerConf(),
          nodeMapper, getMetricRegistry());
      clientNotificationService.addListener(this);
      clientNotificationService.start();
      clientNotificationService.addListener(restData);

      getConf().set(YarnRMLlamaAMConnector.ADVERTISED_HOSTNAME_KEY,
          ThriftEndPoint.getServerAddress(getServerConf()));
      getConf().setInt(YarnRMLlamaAMConnector.ADVERTISED_PORT_KEY,
          ThriftEndPoint.getServerPort(getServerConf()));
      getConf().set(YarnRMLlamaAMConnector.ADVERTISED_TRACKING_URL_KEY,
          getHttpLlamaUI());
      llamaAm = LlamaAM.create(getConf(), restData);
      llamaAm.setMetricRegistry(getMetricRegistry());
      llamaAm.start();
    } catch (Exception ex) {
      throw new RuntimeException(ex);
    }
  }

  @Override
  protected void stopService() {
    llamaAm.stop();
    clientNotificationService.stop();
    stopHttpServer();
  }

  @Override
  protected LlamaAMService.Processor createServiceProcessor() {
    LlamaAMService.Iface handler = new LlamaAMServiceImpl(llamaAm, nodeMapper,
        clientNotificationService);
    MetricLlamaAMService.registerMetric(getMetricRegistry());
    handler = new MetricLlamaAMService(handler, getMetricRegistry());
    return new LlamaAMService.Processor<LlamaAMService.Iface>(handler);
  }

  @Override
  protected LlamaAMAdminService.Processor createAdminServiceProcessor() {
    LlamaAMAdminService.Iface handler = new LlamaAMAdminServiceImpl(llamaAm,
        clientNotificationService);
    return new LlamaAMAdminService.Processor<LlamaAMAdminService.Iface>(handler);
  }

  @Override
  public void onRegister(ClientInfo clientInfo) {
  }

  @Override
  public void onUnregister(ClientInfo clientInfo) {
    try {
      llamaAm.releaseReservationsForHandle(clientInfo.getHandle());
    } catch (Throwable ex) {
      getLog().warn("Error releasing reservations for handle '{}', {}",
          clientInfo.getHandle(), ex.toString(), ex);
    }
  }
}
