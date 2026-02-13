"""
Standalone Timeline Editor for BFEVFL files
Entry point for: python -m eventeditor.timeline
"""

import sys
from PyQt5 import QtWidgets as qw
from PyQt5 import QtCore as qc
import evfl

# Import the timeline editor widget
from eventeditor.timeline_editor import TimelineEditor


class TimelineEditorWindow(qw.QMainWindow):
    """Main window for standalone timeline editor"""
    
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.current_flow = None
        self.timeline_editor = None
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize the main window UI"""
        self.setWindowTitle("EventEditor - Timeline Mode")
        self.resize(1200, 700)
        
        # Create menu bar
        self.create_menus()
        
        # Central widget will be timeline editor (created when file is loaded)
        self.central_placeholder = qw.QLabel(
            "No timeline loaded.\n\n"
            "File → Open to load a timeline file (.bfevfl)"
        )
        self.central_placeholder.setAlignment(qc.Qt.AlignCenter)
        self.central_placeholder.setStyleSheet("color: #888; font-size: 14px;")
        self.setCentralWidget(self.central_placeholder)
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
    def create_menus(self):
        """Create the menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        open_action = qw.QAction("&Open", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        save_action = qw.QAction("&Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        save_as_action = qw.QAction("Save &As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        exit_action = qw.QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = qw.QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def open_file(self):
        """Open a timeline file"""
        filename, _ = qw.QFileDialog.getOpenFileName(
            self,
            "Open Timeline File",
            "",
            "BFEVFL Files (*.bfevfl);;All Files (*.*)"
        )
        
        if not filename:
            return
            
        try:
            # Load the file
            flow = evfl.EventFlow()
            with open(filename, 'rb') as f:
                flow.read(f.read())
            
            # Check if it has timeline data
            if not flow.timeline:
                qw.QMessageBox.warning(
                    self,
                    "No Timeline Data",
                    f"The file '{filename}' does not contain timeline data.\n\n"
                    "This file may be a flowchart-only file. "
                    "Try opening it with the regular EventEditor instead."
                )
                return
            
            # Success!
            self.current_file = filename
            self.current_flow = flow
            self.load_timeline(flow.timeline)
            self.statusBar().showMessage(f"Loaded: {filename}")
            
        except Exception as e:
            qw.QMessageBox.critical(
                self,
                "Error Opening File",
                f"Failed to open file:\n{str(e)}"
            )
            
    def load_timeline(self, timeline):
        """Load timeline data into the editor"""
        # Create timeline editor if it doesn't exist
        if not self.timeline_editor:
            self.timeline_editor = TimelineEditor()
            self.timeline_editor.timeline_modified.connect(self.on_timeline_modified)
            self.setCentralWidget(self.timeline_editor)
        
        # Load the timeline data
        self.timeline_editor.load_timeline(timeline)
        self.setWindowTitle(f"EventEditor - Timeline Mode - {self.current_file}")
        
    def on_timeline_modified(self):
        """Handle timeline modifications"""
        # Mark as modified in window title
        if "*" not in self.windowTitle():
            self.setWindowTitle(self.windowTitle() + " *")
            
    def save_file(self):
        """Save the current timeline"""
        if not self.current_file:
            self.save_file_as()
            return
            
        try:
            # Write the flow back to file
            with open(self.current_file, 'wb') as f:
                self.current_flow.write(f)
            
            # Remove * from title
            title = self.windowTitle().replace(" *", "")
            self.setWindowTitle(title)
            self.statusBar().showMessage(f"Saved: {self.current_file}")
            qw.QMessageBox.information(self, "Saved", "Timeline saved successfully!")
            
        except Exception as e:
            qw.QMessageBox.critical(
                self,
                "Error Saving File",
                f"Failed to save file:\n{str(e)}"
            )
            
    def save_file_as(self):
        """Save the timeline to a new file"""
        if not self.current_flow:
            return
            
        filename, _ = qw.QFileDialog.getSaveFileName(
            self,
            "Save Timeline As",
            "",
            "BFEVFL Files (*.bfevfl);;All Files (*.*)"
        )
        
        if filename:
            self.current_file = filename
            self.save_file()
            
    def show_about(self):
        """Show about dialog"""
        qw.QMessageBox.about(
            self,
            "About Timeline Editor",
            "<h3>EventEditor - Timeline Mode</h3>"
            "<p>Timeline editor for BFEVFL files</p>"
            "<p>Part of the EventEditor project</p>"
            "<p>Fork by: cargocult-mods</p>"
            "<p>Original by: leoetlino</p>"
            "<p>License: GPL-2.0</p>"
        )
        
    def closeEvent(self, event):
        """Handle window close"""
        if "*" in self.windowTitle():
            reply = qw.QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Save before closing?",
                qw.QMessageBox.Save | qw.QMessageBox.Discard | qw.QMessageBox.Cancel
            )
            
            if reply == qw.QMessageBox.Save:
                self.save_file()
                event.accept()
            elif reply == qw.QMessageBox.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    """Main entry point"""
    app = qw.QApplication(sys.argv)
    app.setApplicationName("EventEditor Timeline")
    app.setOrganizationName("cargocult-mods")
    
    # Set dark theme (optional but looks nice)
    app.setStyle("Fusion")
    
    window = TimelineEditorWindow()
    window.show()
    
    # If a file was passed as argument, open it
    if len(sys.argv) > 1:
        # TODO: Open the file
        pass
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
