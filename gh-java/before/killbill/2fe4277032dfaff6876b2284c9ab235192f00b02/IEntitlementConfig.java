/*
 * Copyright 2010-2011 Ning, Inc.
 *
 * Ning licenses this file to you under the Apache License, version 2.0
 * (the "License"); you may not use this file except in compliance with the
 * License.  You may obtain a copy of the License at:
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

package com.ning.billing.entitlement.glue;

import org.skife.config.Config;

public interface IEngineConfig {

    @Config("killbill.entitlement.dao.claim.time")
    public long getDaoClaimTimeMs();

    @Config("killbill.entitlement.dao.ready.max")
    public int getDaoMaxReadyEvents();

    @Config("killbill.entitlement.catalog.config.file")
    public String getCatalogConfigFileName();

    @Config("killbill.entitlement.engine.notifications.sleep")
    public long getNotificationSleepTimeMs();
}
