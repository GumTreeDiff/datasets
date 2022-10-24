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

package com.ning.billing.entitlement.api.billing;

import com.ning.billing.catalog.api.BillingPeriod;
import com.ning.billing.catalog.api.Currency;
import com.ning.billing.catalog.api.IInternationalPrice;
import org.joda.time.DateTime;

import java.math.BigDecimal;
import java.util.UUID;

public interface IBillingEvent extends Comparable<IBillingEvent> {

    /**
     *
     * @return the billCycleDay as seen for that subscription at that time
     *
     * Note: The billCycleDay may come from the Account, or the bundle or the subscription itself
     */
    public int getBillCycleDay();

    /**
     *
     * @return the id for the matching subscription
     */
    public UUID getSubscriptionId();

    /**
     *
     * @return the date for when that event became effective
     */
    public DateTime getEffectiveDate();

    /**
     *
     * @return the name of the plan phase
     */
    public String getPlanPhaseName();


    /**
     *
     * @return the name of the plan
     */
    public String getPlanName();

    /**
     *
     * @return the international price for the event
     *
     */
    public IInternationalPrice getPrice();

    /**
     *
     * @param currency the target currency for invoicing
     * @return the price of the plan phase in the specified currency
     */
    public BigDecimal getPrice(Currency currency);

    /**
     *
     * @return the billing period for the active phase
     */
    public BillingPeriod getBillingPeriod();

    /**
     *
     * @return the billing mode for the current event
     */
    public BillingMode getBillingMode();

    /**
     *
     * @return the description of the billing event
     */
    public String getDescription();
}
