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

package com.ning.billing.entitlement.engine.core;

import java.lang.Thread.UncaughtExceptionHandler;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.Executor;
import java.util.concurrent.Executors;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.atomic.AtomicInteger;

import org.skife.config.Config;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.inject.Inject;
import com.ning.billing.entitlement.engine.dao.IEntitlementDao;
import com.ning.billing.entitlement.events.IEvent;
import com.ning.billing.entitlement.glue.IEngineConfig;
import com.ning.billing.util.clock.IClock;

public abstract class ApiEventProcessorBase implements IApiEventProcessor {

    // Wait for max 60 sec when shutting down the EventProcessor
    private final long STOP_WAIT_TIMEOUT_MS = 60000;

    private static final AtomicInteger sequenceId = new AtomicInteger();

    // STEPH will change at each restart. can we do better?
    protected final UUID apiProcessorId;

    private static final String API_EVENT_THREAD_NAME = "ApiEventNotification";
    protected final static Logger log = LoggerFactory.getLogger(ApiEventProcessor.class);

    protected final IEntitlementDao dao;
    protected final IClock clock;

    private Executor executor;
    private final IEngineConfig config;
    protected IEventListener listener;

    protected long nbProcessedEvents;
    protected volatile boolean isProcessingEvents;

    @Inject
    public ApiEventProcessorBase(IClock clock, IEntitlementDao dao, IEngineConfig config) {
        this.clock = clock;
        this.dao = dao;
        this.config = config;
        this.listener = null;
        this.isProcessingEvents = false;
        this.apiProcessorId = UUID.randomUUID();
        this.nbProcessedEvents = 0;
    }



    @Override
    public void startNotifications(IEventListener listener) {

        this.listener = listener;
        this.isProcessingEvents = true;
        this.nbProcessedEvents = 0;

        final ApiEventProcessorBase apiEventProcessor = this;

        synchronized (this) {

            if (executor != null) {
                log.warn("There is already an executor thread running, return");
                return;
            }

            this.executor = Executors.newSingleThreadExecutor(new ThreadFactory() {

                @Override
                public Thread newThread(Runnable r) {
                    Thread th = new Thread(r);
                    th.setName(API_EVENT_THREAD_NAME);
                    //th.setDaemon(true);
                    th.setUncaughtExceptionHandler(new UncaughtExceptionHandler() {
                        @Override
                        public void uncaughtException(Thread t, Throwable e) {
                            log.error("Uncaught exception for thread " + t.getName(), e);
                        }
                    });
                    return th;
                }
            });
        }

        executor.execute(new Runnable() {
            @Override
            public void run() {

                log.info(String.format("ApiEventProcessor thread %s  [%d] started", API_EVENT_THREAD_NAME,
                        Thread.currentThread().getId()));
                try {
                    while (true) {
                        synchronized (apiEventProcessor) {
                            if (!isProcessingEvents) {
                                log.info(String.format("ApiEventProcessor thread  %s  [%d] exiting...", API_EVENT_THREAD_NAME,
                                        Thread.currentThread().getId()));
                                apiEventProcessor.notify();
                                break;
                            }
                        }

                        // Callback may trigger exceptions in user code so catch anything here and live with it.
                        try {
                            doProcessEvents(sequenceId.getAndIncrement());
                        } catch (OutOfMemoryError e) {
                            log.warn("",e);
                            throw e;
                        } catch (Throwable e) {
                            log.error(API_EVENT_THREAD_NAME + " got an exception", e);
                        }
                        sleepALittle();
                    }
                    log.info(String.format("ApiEventProcessor thread  %s  [%d] exited...", API_EVENT_THREAD_NAME,
                            Thread.currentThread().getId()));
                } catch (Throwable e) {
                    log.error(API_EVENT_THREAD_NAME + " got an exception exiting...", e);
                    // STEPH let's review that later...
                    System.exit(1);
                }
            }

            private void sleepALittle() {
                try {
                    Thread.sleep(config.getNotificationSleepTimeMs());
                } catch (Exception e) {
                    log.warn("Got interrupted exception when sleeeping between event notifications", e);
                }
            }
        });
    }

    @Override
    public void stopNotifications() {
        synchronized(this) {
            isProcessingEvents = false;
            try {
                log.info("ApiEventProcessor requested to stop");
                wait(STOP_WAIT_TIMEOUT_MS);
                executor = null;
                log.info("ApiEventProcessor requested should have exited");
            } catch (InterruptedException e) {
                log.warn("Got interrupted exception when stopping notifications", e);
            }
        }
    }

    protected abstract void doProcessEvents(int sequenceId);
}
