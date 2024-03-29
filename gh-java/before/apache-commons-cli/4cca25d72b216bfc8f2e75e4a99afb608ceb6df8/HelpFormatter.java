/*
 * Copyright (C) The Apache Software Foundation. All rights reserved.
 *
 * This software is published under the terms of the Apache Software License
 * version 1.1, a copy of which has been included with this distribution in
 * the LICENSE file.
 * 
 * $Id: HelpFormatter.java,v 1.2 2002/05/17 11:44:32 jstrachan Exp $
 */
package org.apache.commons.cli;

import java.io.PrintWriter;
import java.util.Iterator;
import java.util.List;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;

/** 
 * A formatter of help messages for the current command line options
 *
 * @author Slawek Zachcial
 **/
public class HelpFormatter
{
   // --------------------------------------------------------------- Constants

   public static final int DEFAULT_WIDTH              = 80;
   public static final int DEFAULT_LEFT_PAD           = 1;
   public static final int DEFAULT_DESC_PAD           = 3;
   public static final String DEFAULT_SYNTAX_PREFIX   = "usage: ";
   public static final String DEFAULT_OPT_PREFIX      = "-";
   public static final String DEFAULT_LONG_OPT_PREFIX = "--";
   public static final String DEFAULT_ARG_NAME        = "arg";

   // ------------------------------------------------------------------ Static

   // -------------------------------------------------------------- Attributes

   public int defaultWidth;
   public int defaultLeftPad;
   public int defaultDescPad;
   public String defaultSyntaxPrefix;
   public String defaultNewLine;
   public String defaultOptPrefix;
   public String defaultLongOptPrefix;
   public String defaultArgName;

   // ------------------------------------------------------------ Constructors
   public HelpFormatter()
   {
      defaultWidth = DEFAULT_WIDTH;
      defaultLeftPad = DEFAULT_LEFT_PAD;
      defaultDescPad = DEFAULT_DESC_PAD;
      defaultSyntaxPrefix = DEFAULT_SYNTAX_PREFIX;
      defaultNewLine = System.getProperty("line.separator");
      defaultOptPrefix = DEFAULT_OPT_PREFIX;
      defaultLongOptPrefix = DEFAULT_LONG_OPT_PREFIX;
      defaultArgName = DEFAULT_ARG_NAME;
   }

   // ------------------------------------------------------------------ Public

   public void printHelp( String cmdLineSyntax,
                          Options options )
   {
      printHelp( defaultWidth, cmdLineSyntax, null, options, null );
   }

   public void printHelp( String cmdLineSyntax,
                          String header,
                          Options options,
                          String footer )
   {
      printHelp(defaultWidth, cmdLineSyntax, header, options, footer);
   }

   public void printHelp( int width,
                          String cmdLineSyntax,
                          String header,
                          Options options,
                          String footer )
   {
      PrintWriter pw = new PrintWriter(System.out);
      printHelp( pw, width, cmdLineSyntax, header,
                 options, defaultLeftPad, defaultDescPad, footer );
      pw.flush();
   }

   public void printHelp( PrintWriter pw,
                          int width,
                          String cmdLineSyntax,
                          String header,
                          Options options,
                          int leftPad,
                          int descPad,
                          String footer )
      throws IllegalArgumentException
   {
      if ( cmdLineSyntax == null || cmdLineSyntax.length() == 0 )
      {
         throw new IllegalArgumentException("cmdLineSyntax not provided");
      }

      printUsage( pw, width, cmdLineSyntax );
      if ( header != null && header.trim().length() > 0 )
      {
         printWrapped( pw, width, header );
      }
      printOptions( pw, width, options, leftPad, descPad );
      if ( footer != null && footer.trim().length() > 0 )
      {
         printWrapped( pw, width, footer );
      }
   }

   public void printUsage( PrintWriter pw, int width, String cmdLineSyntax )
   {
      int argPos = cmdLineSyntax.indexOf(' ') + 1;
      printWrapped(pw, width, defaultSyntaxPrefix.length() + argPos,
                   defaultSyntaxPrefix + cmdLineSyntax);
   }

   public void printOptions( PrintWriter pw, int width, Options options, int leftPad, int descPad )
   {
      StringBuffer sb = new StringBuffer();
      renderOptions(sb, width, options, leftPad, descPad);
      pw.println(sb.toString());
   }

   public void printWrapped( PrintWriter pw, int width, String text )
   {
      printWrapped(pw, width, 0, text);
   }

   public void printWrapped( PrintWriter pw, int width, int nextLineTabStop, String text )
   {
      StringBuffer sb = new StringBuffer(text.length());
      renderWrappedText(sb, width, nextLineTabStop, text);
      pw.println(sb.toString());
   }

   // --------------------------------------------------------------- Protected

   protected StringBuffer renderOptions( StringBuffer sb,
                                         int width,
                                         Options options,
                                         int leftPad,
                                         int descPad )
   {
      final String lpad = createPadding(leftPad);
      final String dpad = createPadding(descPad);

      //first create list containing only <lpad>-a,--aaa where -a is opt and --aaa is
      //long opt; in parallel look for the longest opt string
      //this list will be then used to sort options ascending
      int max = 0;
      StringBuffer optBuf;
      List prefixList = new ArrayList();
      Option option;
      for ( Iterator i = options.getOptions().iterator(); i.hasNext(); )
      {
         option = (Option) i.next();
         optBuf = new StringBuffer(8);
         optBuf.append(lpad).append(defaultOptPrefix).append(option.getOpt());
         if ( option.hasLongOpt() )
         {
            optBuf.append(',').append(defaultLongOptPrefix).append(option.getLongOpt());
         }
         if ( option.hasArg() )
         {
            //FIXME - should have a way to specify arg name per option
            optBuf.append(' ').append(defaultArgName);
         }
         prefixList.add(optBuf);
         max = optBuf.length() > max ? optBuf.length() : max;
      }

      //right pad the prefixes
      for ( Iterator i = prefixList.iterator(); i.hasNext(); )
      {
         optBuf = (StringBuffer) i.next();
         if ( optBuf.length() < max )
         {
            optBuf.append(createPadding(max-optBuf.length()));
         }
         optBuf.append(dpad);
      }

      //sort this list ascending
      Collections.sort(prefixList, new StringBufferComparator());

      //finally render options
      int nextLineTabStop = max + descPad;
      char opt;
      int optOffset = leftPad + defaultOptPrefix.length();

      for ( Iterator i = prefixList.iterator(); i.hasNext(); )
      {
         optBuf = (StringBuffer) i.next();
         opt = optBuf.charAt(optOffset);
         option = options.getOption(opt);
         renderWrappedText(sb, width, nextLineTabStop,
                           optBuf.append(option.getDescription()).toString());
         if ( i.hasNext() )
         {
            sb.append(defaultNewLine);
         }
      }

      return sb;
   }

   protected StringBuffer renderWrappedText( StringBuffer sb,
                                             int width,
                                             int nextLineTabStop,
                                             String text )
   {
      int pos = findWrapPos( text, width, 0);
      if ( pos == -1 )
      {
         sb.append(rtrim(text));
         return sb;
      }
      else
      {
         sb.append(rtrim(text.substring(0, pos))).append(defaultNewLine);
      }

      //all following lines must be padded with nextLineTabStop space characters
      final String padding = createPadding(nextLineTabStop);

      while ( true )
      {
         text = padding + text.substring(pos).trim();
         pos = findWrapPos( text, width, nextLineTabStop );
         if ( pos == -1 )
         {
            sb.append(text);
            return sb;
         }

         sb.append(rtrim(text.substring(0, pos))).append(defaultNewLine);
      }

   }

   /**
    * Finds the next text wrap position after <code>startPos</code> for the text
    * in <code>sb</code> with the column width <code>width</code>.
    * The wrap point is the last postion before startPos+width having a whitespace
    * character (space, \n, \r).
    *
    * @param sb text to be analyzed
    * @param width width of the wrapped text
    * @param startPos position from which to start the lookup whitespace character
    * @return postion on which the text must be wrapped or -1 if the wrap position is at the end
    *         of the text
    */
   protected int findWrapPos( String text, int width, int startPos )
   {
      int pos = -1;
      // the line ends before the max wrap pos or a new line char found
      if ( ((pos = text.indexOf('\n', startPos)) != -1 && pos <= width)  ||
           ((pos = text.indexOf('\t', startPos)) != -1 && pos <= width) )
      {
         return pos;
      }
      else if ( (startPos + width) >= text.length() )
      {
         return -1;
      }

      //look for the last whitespace character before startPos+width
      pos = startPos + width;
      char c;
      while ( pos >= startPos && (c = text.charAt(pos)) != ' ' && c != '\n' && c != '\r' )
      {
         --pos;
      }
      //if we found it - just return
      if ( pos > startPos )
      {
         return pos;
      }
      else
      {
         //must look for the first whitespace chearacter after startPos + width
         pos = startPos + width;
         while ( pos <= text.length() && (c = text.charAt(pos)) != ' ' && c != '\n' && c != '\r' )
         {
            ++pos;
         }
         return pos == text.length() ? -1 : pos;
      }
   }

   protected String createPadding(int len)
   {
      StringBuffer sb = new StringBuffer(len);
      for ( int i = 0; i < len; ++i )
      {
         sb.append(' ');
      }
      return sb.toString();
   }

   protected String rtrim( String s )
   {
      if ( s == null || s.length() == 0 )
      {
         return s;
      }

      int pos = s.length();
      while ( pos >= 0 && Character.isWhitespace(s.charAt(pos-1)) )
      {
         --pos;
      }
      return s.substring(0, pos);
   }

   // ------------------------------------------------------- Package protected
   
   // ----------------------------------------------------------------- Private
   
   // ----------------------------------------------------------- Inner classes

   private static class StringBufferComparator
   implements Comparator
   {
      public int compare( Object o1, Object o2 )
      {
         return ((StringBuffer) o1).toString().compareTo(((StringBuffer) o2).toString());
      }
   }
}
