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
package org.whispersystems.textsecuregcm.controllers;

import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Optional;
import com.yammer.dropwizard.auth.Auth;
import com.yammer.metrics.annotation.Timed;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.whispersystems.textsecuregcm.auth.AuthenticationCredentials;
import org.whispersystems.textsecuregcm.auth.AuthorizationHeader;
import org.whispersystems.textsecuregcm.auth.InvalidAuthorizationHeaderException;
import org.whispersystems.textsecuregcm.entities.AccountAttributes;
import org.whispersystems.textsecuregcm.limits.RateLimiters;
import org.whispersystems.textsecuregcm.storage.Account;
import org.whispersystems.textsecuregcm.storage.AccountsManager;
import org.whispersystems.textsecuregcm.storage.PendingDevicesManager;
import org.whispersystems.textsecuregcm.util.VerificationCode;

import javax.validation.Valid;
import javax.ws.rs.Consumes;
import javax.ws.rs.GET;
import javax.ws.rs.HeaderParam;
import javax.ws.rs.PUT;
import javax.ws.rs.Path;
import javax.ws.rs.PathParam;
import javax.ws.rs.Produces;
import javax.ws.rs.WebApplicationException;
import javax.ws.rs.core.MediaType;
import javax.ws.rs.core.Response;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;

@Path("/v1/devices")
public class DeviceController {

  private final Logger logger = LoggerFactory.getLogger(DeviceController.class);

  private final PendingDevicesManager      pendingDevices;
  private final AccountsManager            accounts;
  private final RateLimiters               rateLimiters;

  public DeviceController(PendingDevicesManager pendingDevices,
                          AccountsManager accounts,
                          RateLimiters rateLimiters)
  {
    this.pendingDevices  = pendingDevices;
    this.accounts        = accounts;
    this.rateLimiters    = rateLimiters;
  }

  @Timed
  @GET
  @Path("")
  @Produces(MediaType.APPLICATION_JSON)
  public VerificationCode createDeviceToken(@Auth Account account)
      throws RateLimitExceededException
  {
    rateLimiters.getVerifyLimiter().validate(account.getNumber()); //TODO: New limiter?

    VerificationCode verificationCode = generateVerificationCode();
    pendingDevices.store(account.getNumber(), verificationCode.getVerificationCode());

    return verificationCode;
  }

  @Timed
  @PUT
  @Produces(MediaType.APPLICATION_JSON)
  @Consumes(MediaType.APPLICATION_JSON)
  @Path("/{verification_code}")
  public long verifyDeviceToken(@PathParam("verification_code") String verificationCode,
                                @HeaderParam("Authorization")   String authorizationHeader,
                                @Valid                          AccountAttributes accountAttributes)
      throws RateLimitExceededException
  {
    Account account;
    try {
      AuthorizationHeader header = AuthorizationHeader.fromFullHeader(authorizationHeader);
      String number              = header.getNumber();
      String password            = header.getPassword();

      rateLimiters.getVerifyLimiter().validate(number); //TODO: New limiter?

      Optional<String> storedVerificationCode = pendingDevices.getCodeForNumber(number);

      if (!storedVerificationCode.isPresent() ||
          !verificationCode.equals(storedVerificationCode.get()))
      {
        throw new WebApplicationException(Response.status(403).build());
      }

      account = new Account();
      account.setNumber(number);
      account.setAuthenticationCredentials(new AuthenticationCredentials(password));
      account.setSignalingKey(accountAttributes.getSignalingKey());
      account.setSupportsSms(accountAttributes.getSupportsSms());
      account.setFetchesMessages(accountAttributes.getFetchesMessages());

      accounts.createAccountOnExistingNumber(account);

      pendingDevices.remove(number);

      logger.debug("Stored new device account...");
    } catch (InvalidAuthorizationHeaderException e) {
      logger.info("Bad Authorization Header", e);
      throw new WebApplicationException(Response.status(401).build());
    }

    return account.getDeviceId();
  }

  @VisibleForTesting protected VerificationCode generateVerificationCode() {
    try {
      SecureRandom random = SecureRandom.getInstance("SHA1PRNG");
      int randomInt       = 100000 + random.nextInt(900000);
      return new VerificationCode(randomInt);
    } catch (NoSuchAlgorithmException e) {
      throw new AssertionError(e);
    }
  }
}
