/*
 * Copyright (C) 2007 Google Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.google.common.io;

import java.io.IOException;

/**
 * An factory for readable streams of bytes or characters.
 *
 * @author Chris Nokleberg
 * @param <T> the type of object being supplied
 * @since 9.09.15 <b>tentative</b>
 */
public interface InputSupplier<T> {
  T getInput() throws IOException;
}
