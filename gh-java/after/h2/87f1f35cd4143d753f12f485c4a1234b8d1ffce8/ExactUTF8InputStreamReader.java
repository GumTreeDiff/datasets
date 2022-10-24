/*
 * Copyright 2004-2006 H2 Group. Licensed under the H2 License, Version 1.0 (http://h2database.com/html/license.html).
 * Initial Developer: H2 Group
 */
package org.h2.util;

import java.io.IOException;
import java.io.InputStream;
import java.io.Reader;

/**
 * The InputStreamReader may read some more bytes than required.
 * If this is a problem, use this class
 */
public class ExactUTF8InputStreamReader extends Reader {
    
    private InputStream in;
    
    public ExactUTF8InputStreamReader(InputStream in) {
        this.in = in;
    }

    public void close() throws IOException {
    }

    public int read(char[] cbuf, int off, int len) throws IOException {
        for(int i=0; i<len; i++, off++) {
            int x = in.read();
            if(x < 0) {
                return i == 0 ? -1 : i;
            }
            x = x & 0xff;
            if(x < 0x80) {
                cbuf[off] = (char)x;
            } else if(x >= 0xe0) {
                cbuf[off] = (char)(((x & 0xf) << 12) + ((in.read() & 0x3f) << 6) + (in.read() & 0x3f));
            } else {
                cbuf[off] = (char)(((x & 0x1f) << 6) + (in.read() & 0x3f));
            }
        }
        return len;
    }

}
