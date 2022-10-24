/*
 * Licensed to Elastic Search and Shay Banon under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership. Elastic Search licenses this
 * file to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.elasticsearch.action.admin.indices.refresh;

import org.elasticsearch.action.support.broadcast.BroadcastShardOperationRequest;

import java.io.DataInput;
import java.io.DataOutput;
import java.io.IOException;

/**
 * @author kimchy (Shay Banon)
 */
public class ShardRefreshRequest extends BroadcastShardOperationRequest {

    private boolean waitForOperations = true;

    ShardRefreshRequest() {
    }

    public ShardRefreshRequest(String index, int shardId, RefreshRequest request) {
        super(index, shardId);
        waitForOperations = request.waitForOperations();
    }

    public boolean waitForOperations() {
        return waitForOperations;
    }

    public ShardRefreshRequest waitForOperations(boolean waitForOperations) {
        this.waitForOperations = waitForOperations;
        return this;
    }

    @Override public void readFrom(DataInput in) throws IOException, ClassNotFoundException {
        super.readFrom(in);
        waitForOperations = in.readBoolean();
    }

    @Override public void writeTo(DataOutput out) throws IOException {
        super.writeTo(out);
        out.writeBoolean(waitForOperations);
    }
}