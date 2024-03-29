/*
Copyright (C) 2003 Nizar N. Batada, Morten O. Alver

All programs in this directory and
subdirectories are published under the GNU General Public License as
described below.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or (at
your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
USA

Further information about the GNU GPL is available at:
http://www.gnu.org/copyleft/gpl.ja.html

*/
package net.sf.jabref;

import java.util.*;

public class Globals {

    private static String resourcePrefix = "resource/JabRef";
    public static ResourceBundle messages;

    /**
     * String constants.
     */
    public static final String
	KEY_FIELD = "bibtexkey",
	SEARCH = "search",
	GROUPSEARCH = "groupsearch";

    public static void setLanguage(String language, String country) {
	messages = ResourceBundle.getBundle(resourcePrefix,
					    new Locale(language,
						       country));

    }

    public static String lang(String key){
	String translation;
	try{
	    translation=Globals.messages.getString(key.replaceAll(" ","_"));
	}catch(MissingResourceException ex){
	    translation= key;
	    System.err.println("Warning: could not get translation for \""
			       + key +"\"");
	}
	return translation.replaceAll("_"," ");
    }

}
