/*
Copyright (C) 2003  Morten O. Alver and Nizar N. Batada

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
import java.io.*;
import javax.swing.*;
import javax.swing.plaf.*;
import java.awt.event.*;
import javax.swing.plaf.basic.*;
import javax.swing.plaf.metal.*;

//======================================================================
// this class is a work around for the problem with regular filechooser:
// single clicking will no longer put into edit mode
//======================================================================
public class JabRefFileChooser extends JFileChooser {
    public JabRefFileChooser(){
	super();
    }

    public JabRefFileChooser(File file){
	super(file);
    }

    //========================================================
    //
    //========================================================
    
    protected void setUI(ComponentUI newUI) {
	 super.setUI(new JabRefUI(this));
     }
    //========================================================
    //
    //========================================================

    public static void main(String[] args) {
	JabRefFileChooser fc = new JabRefFileChooser();
	int returnVal = fc.showOpenDialog(null);
	if (returnVal == JFileChooser.APPROVE_OPTION) {
	    File file = fc.getSelectedFile();
	}
    }
}


class JabRefUI extends MetalFileChooserUI {
    public JabRefUI(JFileChooser filechooser) {
	super(filechooser);
    }
    protected class DoubleClickListener extends BasicFileChooserUI.DoubleClickListener {
	JList list;
	public DoubleClickListener(JList list) {
	    super(list);
	    this.list = list;
	}
	public void mouseEntered(MouseEvent e) {
	    //System.out.println("mouse entered");
	    MouseListener [] l = list.getMouseListeners();
	    for (int i = 0; i < l.length; i++) {
		if (l[i] instanceof MetalFileChooserUI.SingleClickListener) {
		    list.removeMouseListener(l[i]);
		}
	    }
	    super.mouseEntered(e);
	}
    }
    protected MouseListener createDoubleClickListener(JFileChooser fc, JList list) {
	return new DoubleClickListener(list);
    }
} 
