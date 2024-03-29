/*
 * $Header: /home/cvs/jakarta-commons-sandbox/cli/src/java/org/apache/commons/cli/Option.java,v 1.6 2002/06/06 22:50:14 bayard Exp $
 * $Revision: 1.6 $
 * $Date: 2002/06/06 22:50:14 $
 *
 * ====================================================================
 *
 * The Apache Software License, Version 1.1
 *
 * Copyright (c) 1999-2001 The Apache Software Foundation.  All rights
 * reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 *
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in
 *    the documentation and/or other materials provided with the
 *    distribution.
 *
 * 3. The end-user documentation included with the redistribution, if
 *    any, must include the following acknowlegement:
 *       "This product includes software developed by the
 *        Apache Software Foundation (http://www.apache.org/)."
 *    Alternately, this acknowlegement may appear in the software itself,
 *    if and wherever such third-party acknowlegements normally appear.
 *
 * 4. The names "The Jakarta Project", "Commons", and "Apache Software
 *    Foundation" must not be used to endorse or promote products derived
 *    from this software without prior written permission. For written
 *    permission, please contact apache@apache.org.
 *
 * 5. Products derived from this software may not be called "Apache"
 *    nor may "Apache" appear in their names without prior written
 *    permission of the Apache Group.
 *
 * THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESSED OR IMPLIED
 * WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
 * OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED.  IN NO EVENT SHALL THE APACHE SOFTWARE FOUNDATION OR
 * ITS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
 * USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
 * OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
 * SUCH DAMAGE.
 * ====================================================================
 *
 * This software consists of voluntary contributions made by many
 * individuals on behalf of the Apache Software Foundation.  For more
 * information on the Apache Software Foundation, please see
 * <http://www.apache.org/>.
 *
 */

/*
 * Copyright (C) The Apache Software Foundation. All rights reserved.
 *
 * This software is published under the terms of the Apache Software License
 * version 1.1, a copy of which has been included with this distribution in
 * the LICENSE file.
 * 
 * $Id: Option.java,v 1.6 2002/06/06 22:50:14 bayard Exp $
 */

package org.apache.commons.cli;

import java.util.ArrayList;

/** <p>Describes a single command-line option.  It maintains
 * information regarding the short-name of the option, the long-name,
 * if any exists, a flag indicating if an argument is required for
 * this option, and a self-documenting description of the option.</p>
 *
 * <p>An Option is not created independantly, but is create through
 * an instance of {@link Options}.<p>
 *
 * @see org.apache.commons.cli.Options
 * @see org.apache.commons.cli.CommandLine
 *
 * @author bob mcwhirter (bob @ werken.com)
 * @author <a href="mailto:jstrachan@apache.org">James Strachan</a>
 * @version $Revision: 1.6 $
 */

public class Option {
    
    /** opt the single character representation of the option */
    private Character  opt          = null;

    /** longOpt is the long representation of the option */
    private String     longOpt      = null;

    /** hasArg specifies whether this option has an associated argument */
    private boolean    hasArg       = false;

    /** description of the option */
    private String     description  = null;

    /** required specifies whether this option is required to be present */
    private boolean    required     = false;

    /** multipleArgs specifies whether this option has multiple argument values */
    private boolean    multipleArgs = false;   

    /** the type of this Option */
    private Object     type         = null;   

    /** ?? **/
    private ArrayList  values       = new ArrayList();
    

    /**
     * Creates an Option using the specified parameters.
     *
     * @param opt character representation of the option
     * @param hasArg specifies whether the Option takes an argument or not
     * @param description describes the function of the option
     */
    public Option(char opt, boolean hasArg, String description) {
        this(opt, null, hasArg, description, false, false);
    }
    
    /**
     * Creates an Option using the specified parameters.
     *
     * @param opt character representation of the option
     * @param longOpt the long representation of the option
     * @param hasArg specifies whether the Option takes an argument or not
     * @param description describes the function of the option
     */
    public Option(char opt, String longOpt, boolean hasArg, String description) {
        this(opt, longOpt, hasArg, description, false, false );
    }

    /**
     * Creates an Option using the specified parameters.
     *
     * @param opt character representation of the option
     * @param longOpt the long representation of the option
     * @param hasArg specifies whether the Option takes an argument or not
     * @param description describes the function of the option
     * @param required specifies whether the option is required or not
     */
    public Option(char opt, String longOpt, boolean hasArg, String description,
                  boolean required ) {
        this(opt, longOpt, hasArg, description, required, false );
    }

    /**
     * Creates an Option using the specified parameters.
     *
     * @param opt character representation of the option
     * @param longOpt the long representation of the option
     * @param hasArg specifies whether the Option takes an argument or not
     * @param description describes the function of the option
     * @param required specifies whether the option is required or not
     * @param multipleArgs specifies whether the option has multiple argument 
     * values
     */
    public Option(char opt, String longOpt, boolean hasArg, String description, 
                  boolean required, boolean multipleArgs ) {
        this(opt, longOpt, hasArg, description, required, multipleArgs, null );
    }
    public Option(char opt, String longOpt, boolean hasArg, String description, 
                  boolean required, boolean multipleArgs, Object type ) {
        this.opt          = new Character( opt );
        this.longOpt      = longOpt;
        this.hasArg       = hasArg;
        this.description  = description;
        this.required     = required;
        this.multipleArgs = multipleArgs;
        this.type         = type;
    }
    
    /** <p>Retrieve the single-character name of this Option</p>
     *
     * <p>It is this character which can be used with
     * {@link CommandLine#hasOption(char opt)} and
     * {@link CommandLine#getOptionValue(char opt)} to check
     * for existence and argument.<p>
     *
     * @return Single character name of this option
     */
    public char getOpt() {
        return this.opt.charValue();
    }

    public Object getType() {
        return this.type;
    }
    
    /** <p>Retrieve the long name of this Option</p>
     *
     * @return Long name of this option, or null, if there is no long name
     */
    public String getLongOpt() {
        return this.longOpt;
    }
    
    /** <p>Query to see if this Option has a long name</p>
     *
     * @return boolean flag indicating existence of a long name
     */
    public boolean hasLongOpt() {
        return ( this.longOpt != null );
    }
    
    /** <p>Query to see if this Option requires an argument</p>
     *
     * @return boolean flag indicating if an argument is required
     */
    public boolean hasArg() {
        return this.hasArg;
    }
    
    /** <p>Retrieve the self-documenting description of this Option</p>
     *
     * @return The string description of this option
     */
    public String getDescription() {
        return this.description;
    }

     /** <p>Query to see if this Option requires an argument</p>
      *
      * @return boolean flag indicating if an argument is required
      */
     public boolean isRequired() {
         return this.required;
     }

     /** <p>Query to see if this Option can take multiple values</p>
      *
      * @return boolean flag indicating if multiple values are allowed
      */
     public boolean hasMultipleArgs() {
         return this.multipleArgs;
     }

    /** <p>Dump state, suitable for debugging.</p>
     *
     * @return Stringified form of this object
     */
    public String toString() {
        StringBuffer buf = new StringBuffer().append("[ option: ");
        
        buf.append( this.opt );
        
        if ( this.longOpt != null ) {
            buf.append(" ")
            .append(this.longOpt);
        }
        
        buf.append(" ");
        
        if ( hasArg ) {
            buf.append( "+ARG" );
        }
        
        buf.append(" :: ")
        .append( this.description );
        
        if ( this.type != null ) {
            buf.append(" :: ")
            .append( this.type );
        }

        buf.append(" ]");
        return buf.toString();
    }

    /**
     * Adds the specified value to this Option
     * 
     * @param value is a/the value of this Option
     */
    public void addValue( String value ) {
        this.values.add( value );
    }

    /**
     * @return the value/first value of this Option or null if there are no
     * values
     */
    public String getValue() {
        return this.values.size()==0 ? null : (String)this.values.get( 0 );
    }

    /**
     * @return the values of this Option or null if there are no
     * values
     */
    public String[] getValues() {
        return this.values.size()==0 ? null : (String[])this.values.toArray(new String[]{});
    }
}
