#!/usr/bin/env groovy

/*
 * All actual logic is in com.cloudera.kitchen.staging.TarballPackageVersions.
 */

@GrabResolver(name='cloudera-snap', root='https://repository.cloudera.com/artifactory/libs-snapshot')
@Grab(group='com.cloudera.kitchen', module='package-tools', version='0.5-SNAPSHOT')
@Grab(group ="org.apache.ant", module = "ant-jsch", version ="1.8.1")
@Grab(group ="com.jcraft", module = "jsch", version ="0.1.42")
@GrabConfig(systemClassLoader = true)

import com.cloudera.kitchen.staging.*

new TarballPackageVersions().callScript(this.args)