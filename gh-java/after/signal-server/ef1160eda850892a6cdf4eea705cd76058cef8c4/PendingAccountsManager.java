/**
 * Copyright (C) 2013 Open WhisperSystems
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
package org.whispersystems.textsecuregcm.storage;

import com.google.common.base.Optional;
import net.spy.memcached.MemcachedClient;

public class PendingAccountsManager {

  private static final String MEMCACHE_PREFIX = "pending_account";

  private final PendingAccounts pendingAccounts;
  private final MemcachedClient memcachedClient;

  public PendingAccountsManager(PendingAccounts pendingAccounts,
                                MemcachedClient memcachedClient)
  {
    this.pendingAccounts = pendingAccounts;
    this.memcachedClient = memcachedClient;
  }

  public void store(String number, String code) {
    if (memcachedClient != null) {
      memcachedClient.set(MEMCACHE_PREFIX + number, 0, code);
    }

    pendingAccounts.insert(number, code);
  }

  public void remove(String number) {
    if (memcachedClient != null)
      memcachedClient.delete(MEMCACHE_PREFIX + number);
    pendingAccounts.remove(number);
  }

  public Optional<String> getCodeForNumber(String number) {
    String code = null;

    if (memcachedClient != null) {
      code = (String)memcachedClient.get(MEMCACHE_PREFIX + number);
    }

    if (code == null) {
      code = pendingAccounts.getCodeForNumber(number);

      if (code != null && memcachedClient != null) {
        memcachedClient.set(MEMCACHE_PREFIX + number, 0, code);
      }
    }

    if (code != null) return Optional.of(code);
    else              return Optional.absent();
  }
}
