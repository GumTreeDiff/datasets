/*
 * Copyright (C) The Apache Software Foundation. All rights reserved.
 *
 * This software is published under the terms of the Apache Software License
 * version 1.1, a copy of which has been included with this distribution in
 * the LICENSE file.
 * 
 * $Id: OptionGroupTest.java,v 1.1 2002/04/23 16:08:02 jstrachan Exp $
 */

package org.apache.commons.cli;

import junit.framework.Test;
import junit.framework.TestCase;
import junit.framework.TestSuite;

/**
 * @author John Keyes (john at integralsource.com)
 * @version $Revision: 1.1 $
 */
public class OptionGroupTest extends TestCase
{

    private Options _options = null;

    public static Test suite() 
    { 
        return new TestSuite ( OptionGroupTest.class ); 
    }

    public OptionGroupTest( String name )
    {
        super( name );
    }

    public void setUp()
    {
        Option file = new Option( "f", "file", false, "file to process" );
        Option dir = new Option( "d", "directory", false, "directory to process" );
        OptionGroup group = new OptionGroup();
        group.addOption( file );
        group.addOption( dir );
        _options = new Options().addOptionGroup( group );

        Option section = new Option( "s", "section", false, "section to process" );
        Option chapter = new Option( "c", "chapter", false, "chapter to process" );
        OptionGroup group2 = new OptionGroup();
        group2.addOption( section );
        group2.addOption( chapter );

        _options.addOptionGroup( group2 );
        _options.addOption( "r", "revision", false, "revision number" );
    }

    public void tearDown()
    {
    }

    public void testSingleOptionFromGroup()
    {
        String[] args = new String[] { "-f" };

        try
        {
            CommandLine cl = _options.parse(args);

            assertTrue( "Confirm -r is NOT set", !cl.hasOption("r") );
            assertTrue( "Confirm -f is set", cl.hasOption("f") );
            assertTrue( "Confirm -d is NOT set", !cl.hasOption("d") );
            assertTrue( "Confirm -s is NOT set", !cl.hasOption("s") );
            assertTrue( "Confirm -c is NOT set", !cl.hasOption("c") );
            assertTrue( "Confirm no extra args", cl.getArgList().size() == 0);
        }
        catch (ParseException e)
        {
            fail( e.toString() );
        }
    }

    public void testSingleOption()
    {
        String[] args = new String[] { "-r" };

        try
        {
            CommandLine cl = _options.parse(args);

            assertTrue( "Confirm -r is set", cl.hasOption("r") );
            assertTrue( "Confirm -f is NOT set", !cl.hasOption("f") );
            assertTrue( "Confirm -d is NOT set", !cl.hasOption("d") );
            assertTrue( "Confirm -s is NOT set", !cl.hasOption("s") );
            assertTrue( "Confirm -c is NOT set", !cl.hasOption("c") );
            assertTrue( "Confirm no extra args", cl.getArgList().size() == 0);
        }
        catch (ParseException e)
        {
            fail( e.toString() );
        }
    }

    public void testTwoValidOptions()
    {
        String[] args = new String[] { "-r", "-f" };

        try
        {
            CommandLine cl = _options.parse(args);

            assertTrue( "Confirm -r is set", cl.hasOption("r") );
            assertTrue( "Confirm -f is set", cl.hasOption("f") );
            assertTrue( "Confirm -d is NOT set", !cl.hasOption("d") );
            assertTrue( "Confirm -s is NOT set", !cl.hasOption("s") );
            assertTrue( "Confirm -c is NOT set", !cl.hasOption("c") );
            assertTrue( "Confirm no extra args", cl.getArgList().size() == 0);
        }
        catch (ParseException e)
        {
            fail( e.toString() );
        }
    }

    public void testSingleLongOption()
    {
        String[] args = new String[] { "--file" };

        try
        {
            CommandLine cl = _options.parse(args);

            assertTrue( "Confirm -r is NOT set", !cl.hasOption("r") );
            assertTrue( "Confirm -f is set", cl.hasOption("f") );
            assertTrue( "Confirm -d is NOT set", !cl.hasOption("d") );
            assertTrue( "Confirm -s is NOT set", !cl.hasOption("s") );
            assertTrue( "Confirm -c is NOT set", !cl.hasOption("c") );
            assertTrue( "Confirm no extra args", cl.getArgList().size() == 0);
        }
        catch (ParseException e)
        {
            fail( e.toString() );
        }
    }

    public void testTwoValidLongOptions()
    {
        String[] args = new String[] { "--revision", "--file" };

        try
        {
            CommandLine cl = _options.parse(args);

            assertTrue( "Confirm -r is set", cl.hasOption("r") );
            assertTrue( "Confirm -f is set", cl.hasOption("f") );
            assertTrue( "Confirm -d is NOT set", !cl.hasOption("d") );
            assertTrue( "Confirm -s is NOT set", !cl.hasOption("s") );
            assertTrue( "Confirm -c is NOT set", !cl.hasOption("c") );
            assertTrue( "Confirm no extra args", cl.getArgList().size() == 0);
        }
        catch (ParseException e)
        {
            fail( e.toString() );
        }
    }

    public void testNoOptionsExtraArgs()
    {
        String[] args = new String[] { "arg1", "arg2" };

        try
        {
            CommandLine cl = _options.parse(args);

            assertTrue( "Confirm -r is NOT set", !cl.hasOption("r") );
            assertTrue( "Confirm -f is NOT set", !cl.hasOption("f") );
            assertTrue( "Confirm -d is NOT set", !cl.hasOption("d") );
            assertTrue( "Confirm -s is NOT set", !cl.hasOption("s") );
            assertTrue( "Confirm -c is NOT set", !cl.hasOption("c") );
            assertTrue( "Confirm TWO extra args", cl.getArgList().size() == 2);
        }
        catch (ParseException e)
        {
            fail( e.toString() );
        }
    }

    public void testTwoOptionsFromGroup()
    {
        String[] args = new String[] { "-f", "-d" };

        try
        {
            CommandLine cl = _options.parse(args);
            fail( "two arguments from group not allowed" );
        }
        catch (ParseException e)
        {
            if( !( e instanceof AlreadySelectedException ) )
            {
                fail( "incorrect exception caught:" + e.getMessage() );
            }
        }
    }

    public void testTwoLongOptionsFromGroup()
    {
        String[] args = new String[] { "--file", "--directory" };

        try
        {
            CommandLine cl = _options.parse(args);
            fail( "two arguments from group not allowed" );
        }
        catch (ParseException e)
        {
            if( !( e instanceof AlreadySelectedException ) )
            {
                fail( "incorrect exception caught:" + e.getMessage() );
            }
        }
    }

    public void testTwoOptionsFromDifferentGroup()
    {
        String[] args = new String[] { "-f", "-s" };

        try
        {
            CommandLine cl = _options.parse(args);
            assertTrue( "Confirm -r is NOT set", !cl.hasOption("r") );
            assertTrue( "Confirm -f is set", cl.hasOption("f") );
            assertTrue( "Confirm -d is NOT set", !cl.hasOption("d") );
            assertTrue( "Confirm -s is set", cl.hasOption("s") );
            assertTrue( "Confirm -c is NOT set", !cl.hasOption("c") );
            assertTrue( "Confirm NO extra args", cl.getArgList().size() == 0);
        }
        catch (ParseException e)
        {
            fail( e.toString() );
        }
    }


}
