/*
 * Copyright (C) The Apache Software Foundation. All rights reserved.
 *
 * This software is published under the terms of the Apache Software License
 * version 1.1, a copy of which has been included with this distribution in
 * the LICENSE file.
 * 
 * $Id: PatternOptionBuilderTest.java,v 1.1 2002/06/06 22:09:25 bayard Exp $
 */
package org.apache.commons.cli;

import junit.framework.TestCase;
import junit.framework.TestSuite;

import java.io.StringWriter;
import java.io.PrintWriter;

/** 
 * Test case for the PatternOptionBuilder class 
 *
 * @author Henri Yandell
 **/
public class PatternOptionBuilderTest
extends TestCase
{
   public static void main( String[] args )
   {
      String[] testName = { PatternOptionBuilderTest.class.getName() };
      junit.textui.TestRunner.main(testName);
   }

   public static TestSuite suite()
   {
      return new TestSuite(PatternOptionBuilderTest.class);
   }

   public PatternOptionBuilderTest( String s )
   {
      super( s );
   }

   public void testSimplePattern()
      throws Exception
   {
      Options options = PatternOptionBuilder.parsePattern("a:b@cde>f+n%t/");
      String[] args = new String[] { "-c", "-a", "foo", "-b", "java.util.Vector", "-e", "build.xml", "-f", "java.util.Calendar", "-n", "4.5", "-t", "http://jakarta.apache.org/" };
      
      CommandLine line = options.parse(args);
      assertEquals("flag a", "foo", line.getOptionValue("a"));
      assertEquals("string flag a", "foo", line.getOptionObject("a"));
      assertEquals("object flag b", new java.util.Vector(), line.getOptionObject("b"));
      assertEquals("boolean true flag c", true, line.hasOption("c"));
      assertEquals("boolean false flag d", false, line.hasOption("d"));
      assertEquals("file flag e", new java.io.File("build.xml"), line.getOptionObject("e"));
      assertEquals("class flag f", java.util.Calendar.class, line.getOptionObject("f"));
      assertEquals("number flag n", new Float(4.5), line.getOptionObject("n"));
      assertEquals("url flag t", new java.net.URL("http://jakarta.apache.org/"), line.getOptionObject("t"));
/// DATES NOT SUPPORTED YET.
//      assertEquals("number flag t", new java.util.Date(1023400137276L), line.getOptionObject('z'));
//     input is:  "Thu Jun 06 17:48:57 EDT 2002"
   }

}
