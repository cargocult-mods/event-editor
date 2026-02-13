"""
Timeline Editor for EventEditor
Adds support for viewing and editing BFEVFL timeline files
"""

import sys
from PyQt5 import QtWidgets as qw
from PyQt5 import QtCore as qc
from PyQt5 import QtGui as qg
from PyQt5.QtWebEngineWidgets import QWebEngineView
import json

class TimelineEditor(qw.QWidget):
    """Main timeline editor widget"""
    
    clip_selected = qc.pyqtSignal(object)  # Emits when clip is selected
    timeline_modified = qc.pyqtSignal()    # Emits when timeline is modified
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.timeline = None
        self.selected_clip = None
        self.zoom_level = 1.0  # pixels per second
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize the UI components"""
        layout = qw.QVBoxLayout()
        
        # Toolbar
        self.toolbar = self.create_toolbar()
        layout.addWidget(self.toolbar)
        
        # Splitter for timeline view and properties
        splitter = qw.QSplitter(qc.Qt.Vertical)
        
        # Timeline view (WebEngine for rendering)
        self.timeline_view = QWebEngineView()
        splitter.addWidget(self.timeline_view)
        
        # Properties panel
        self.properties_panel = TimelinePropertiesPanel()
        self.properties_panel.clip_modified.connect(self.on_clip_modified)
        splitter.addWidget(self.properties_panel)
        
        # Set initial sizes (timeline view gets 70%, properties 30%)
        splitter.setSizes([700, 300])
        
        layout.addWidget(splitter)
        self.setLayout(layout)
        
    def create_toolbar(self):
        """Create the timeline toolbar"""
        toolbar = qw.QToolBar()
        
        # Add clip button
        add_clip_action = qw.QAction("Add Clip", self)
        add_clip_action.triggered.connect(self.add_clip)
        add_clip_action.setIcon(self.style().standardIcon(qw.QStyle.SP_FileIcon))
        toolbar.addAction(add_clip_action)
        
        # Delete clip button
        delete_clip_action = qw.QAction("Delete", self)
        delete_clip_action.triggered.connect(self.delete_selected_clip)
        delete_clip_action.setIcon(self.style().standardIcon(qw.QStyle.SP_TrashIcon))
        toolbar.addAction(delete_clip_action)
        
        toolbar.addSeparator()
        
        # Zoom controls
        zoom_in_action = qw.QAction("Zoom In", self)
        zoom_in_action.triggered.connect(self.zoom_in)
        zoom_in_action.setIcon(self.style().standardIcon(qw.QStyle.SP_ArrowUp))
        toolbar.addAction(zoom_in_action)
        
        zoom_out_action = qw.QAction("Zoom Out", self)
        zoom_out_action.triggered.connect(self.zoom_out)
        zoom_out_action.setIcon(self.style().standardIcon(qw.QStyle.SP_ArrowDown))
        toolbar.addAction(zoom_out_action)
        
        toolbar.addSeparator()
        
        # Time display
        self.time_label = qw.QLabel("00:00.00")
        toolbar.addWidget(self.time_label)
        
        return toolbar
        
    def load_timeline(self, timeline):
        """Load timeline data and render it"""
        self.timeline = timeline
        self.render_timeline()
        
    def render_timeline(self):
        """Render the timeline view"""
        if not self.timeline:
            return
            
        # Generate HTML/JS for timeline visualization
        html = self.generate_timeline_html()
        self.timeline_view.setHtml(html)
        
        # Set up JavaScript bridge for interaction
        self.setup_js_bridge()
        
    def generate_timeline_html(self):
        """Generate HTML for timeline visualization"""
        # Prepare timeline data for JavaScript
        timeline_data = self.prepare_timeline_data()
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            margin: 0;
            padding: 20px;
            font-family: Arial, sans-serif;
            background: #2b2b2b;
            color: #ffffff;
            overflow-x: auto;
        }}
        #timeline-container {{
            position: relative;
            min-height: 500px;
        }}
        .track {{
            position: relative;
            height: 40px;
            margin-bottom: 5px;
            background: #3a3a3a;
            border-radius: 3px;
        }}
        .track-label {{
            position: absolute;
            left: 10px;
            top: 10px;
            font-weight: bold;
            font-size: 12px;
            color: #aaa;
            z-index: 10;
        }}
        .clip {{
            position: absolute;
            height: 35px;
            top: 2.5px;
            border-radius: 3px;
            cursor: pointer;
            border: 2px solid transparent;
            transition: border-color 0.2s;
            overflow: hidden;
        }}
        .clip:hover {{
            border-color: #fff;
        }}
        .clip.selected {{
            border-color: #4a9eff;
            box-shadow: 0 0 10px #4a9eff;
        }}
        .clip-label {{
            padding: 5px;
            font-size: 11px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .time-ruler {{
            height: 30px;
            background: #1a1a1a;
            border-bottom: 1px solid #555;
            position: relative;
            margin-bottom: 10px;
        }}
        .time-marker {{
            position: absolute;
            bottom: 0;
            font-size: 10px;
            color: #888;
        }}
        .time-line {{
            position: absolute;
            bottom: 0;
            width: 1px;
            height: 10px;
            background: #555;
        }}
        /* Clip type colors */
        .clip-type-camera {{ background: #4a9eff; }}
        .clip-type-action {{ background: #5cb85c; }}
        .clip-type-audio {{ background: #f0ad4e; }}
        .clip-type-event {{ background: #d9534f; }}
        .clip-type-effect {{ background: #9b59b6; }}
        .clip-type-default {{ background: #777; }}
    </style>
</head>
<body>
    <div class="time-ruler" id="time-ruler"></div>
    <div id="timeline-container"></div>
    
    <script>
        const timelineData = {json.dumps(timeline_data)};
        const pixelsPerSecond = {self.zoom_level * 60};
        let selectedClip = null;
        
        function renderTimeline() {{
            const container = document.getElementById('timeline-container');
            container.innerHTML = '';
            
            // Group clips by actor/track
            const tracks = groupClipsByTrack(timelineData.clips);
            
            // Render each track
            Object.keys(tracks).forEach(trackName => {{
                const track = createTrack(trackName, tracks[trackName]);
                container.appendChild(track);
            }});
            
            // Render time ruler
            renderTimeRuler();
        }}
        
        function groupClipsByTrack(clips) {{
            const tracks = {{}};
            clips.forEach(clip => {{
                const trackName = clip.actor || clip.type || 'Unnamed';
                if (!tracks[trackName]) {{
                    tracks[trackName] = [];
                }}
                tracks[trackName].push(clip);
            }});
            return tracks;
        }}
        
        function createTrack(name, clips) {{
            const track = document.createElement('div');
            track.className = 'track';
            
            const label = document.createElement('div');
            label.className = 'track-label';
            label.textContent = name;
            track.appendChild(label);
            
            clips.forEach(clip => {{
                const clipEl = createClip(clip);
                track.appendChild(clipEl);
            }});
            
            return track;
        }}
        
        function createClip(clip) {{
            const clipEl = document.createElement('div');
            clipEl.className = 'clip clip-type-' + (clip.type || 'default').toLowerCase();
            clipEl.dataset.clipId = clip.id;
            
            const startPx = clip.start_time * pixelsPerSecond;
            const widthPx = clip.duration * pixelsPerSecond;
            
            clipEl.style.left = startPx + 'px';
            clipEl.style.width = Math.max(widthPx, 30) + 'px';  // Minimum 30px width
            
            const label = document.createElement('div');
            label.className = 'clip-label';
            label.textContent = clip.name;
            clipEl.appendChild(label);
            
            clipEl.onclick = () => selectClip(clip);
            
            return clipEl;
        }}
        
        function selectClip(clip) {{
            // Remove previous selection
            if (selectedClip) {{
                document.querySelectorAll('.clip').forEach(el => {{
                    el.classList.remove('selected');
                }});
            }}
            
            // Add new selection
            selectedClip = clip;
            const clipEl = document.querySelector(`[data-clip-id="${{clip.id}}"]`);
            if (clipEl) {{
                clipEl.classList.add('selected');
            }}
            
            // Notify Python side
            window.pyBridge.clipSelected(JSON.stringify(clip));
        }}
        
        function renderTimeRuler() {{
            const ruler = document.getElementById('time-ruler');
            ruler.innerHTML = '';
            
            const maxTime = Math.max(...timelineData.clips.map(c => c.start_time + c.duration)) + 5;
            const majorInterval = 5;  // Major markers every 5 seconds
            const minorInterval = 1;  // Minor markers every 1 second
            
            for (let t = 0; t <= maxTime; t += minorInterval) {{
                const marker = document.createElement('div');
                marker.className = 'time-line';
                marker.style.left = (t * pixelsPerSecond) + 'px';
                
                if (t % majorInterval === 0) {{
                    marker.style.height = '20px';
                    const label = document.createElement('div');
                    label.className = 'time-marker';
                    label.style.left = (t * pixelsPerSecond + 5) + 'px';
                    label.textContent = t + 's';
                    ruler.appendChild(label);
                }}
                
                ruler.appendChild(marker);
            }}
        }}
        
        // Initial render
        renderTimeline();
    </script>
</body>
</html>
        """
        
        return html
        
    def prepare_timeline_data(self):
        """Convert timeline data to JSON-serializable format"""
        if not self.timeline:
            return {'clips': []}
            
        clips_data = []
        
        # Access clips from timeline
        clips = getattr(self.timeline, 'clips', [])
        
        for i, clip in enumerate(clips):
            clip_dict = {
                'id': i,
                'name': getattr(clip, 'name', f'Clip_{i}'),
                'start_time': getattr(clip, 'start_time', 0.0),
                'duration': getattr(clip, 'duration', 1.0),
                'type': getattr(clip, 'type', 'action'),
                'actor': getattr(clip, 'actor_identifier', None),
            }
            clips_data.append(clip_dict)
            
        return {'clips': clips_data}
        
    def setup_js_bridge(self):
        """Setup JavaScript <-> Python bridge for interaction"""
        # This would use QWebChannel in a full implementation
        # For now, we'll handle it through URL schemes or other methods
        pass
        
    def on_clip_selected(self, clip_data):
        """Handle clip selection from timeline view"""
        # Find the actual clip object
        clips = getattr(self.timeline, 'clips', [])
        clip_id = clip_data.get('id', -1)
        
        if 0 <= clip_id < len(clips):
            self.selected_clip = clips[clip_id]
            self.properties_panel.load_clip(self.selected_clip)
            
    def on_clip_modified(self):
        """Handle clip modification from properties panel"""
        self.timeline_modified.emit()
        self.render_timeline()  # Re-render to show changes
        
    def add_clip(self):
        """Add a new clip to the timeline"""
        dialog = AddClipDialog(self.timeline, self)
        if dialog.exec_() == qw.QDialog.Accepted:
            # Clip was added to timeline in dialog
            self.timeline_modified.emit()
            self.render_timeline()
            
    def delete_selected_clip(self):
        """Delete the currently selected clip"""
        if not self.selected_clip:
            qw.QMessageBox.warning(self, "No Selection", "Please select a clip to delete.")
            return
            
        reply = qw.QMessageBox.question(
            self, 
            "Delete Clip",
            f"Delete clip '{self.selected_clip.name}'?",
            qw.QMessageBox.Yes | qw.QMessageBox.No
        )
        
        if reply == qw.QMessageBox.Yes:
            # Remove from timeline
            clips = getattr(self.timeline, 'clips', [])
            if self.selected_clip in clips:
                clips.remove(self.selected_clip)
                self.selected_clip = None
                self.properties_panel.clear()
                self.timeline_modified.emit()
                self.render_timeline()
                
    def zoom_in(self):
        """Increase zoom level"""
        self.zoom_level = min(self.zoom_level * 1.5, 10.0)
        self.render_timeline()
        
    def zoom_out(self):
        """Decrease zoom level"""
        self.zoom_level = max(self.zoom_level / 1.5, 0.1)
        self.render_timeline()


class TimelinePropertiesPanel(qw.QWidget):
    """Properties panel for editing selected clip"""
    
    clip_modified = qc.pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_clip = None
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize the properties UI"""
        layout = qw.QFormLayout()
        
        # Title
        title = qw.QLabel("<b>Clip Properties</b>")
        layout.addRow(title)
        
        # Name
        self.name_edit = qw.QLineEdit()
        self.name_edit.setPlaceholderText("Clip name")
        layout.addRow("Name:", self.name_edit)
        
        # Start time
        self.start_spin = qw.QDoubleSpinBox()
        self.start_spin.setRange(0.0, 9999.0)
        self.start_spin.setDecimals(2)
        self.start_spin.setSuffix(" sec")
        layout.addRow("Start Time:", self.start_spin)
        
        # Duration
        self.duration_spin = qw.QDoubleSpinBox()
        self.duration_spin.setRange(0.01, 9999.0)
        self.duration_spin.setDecimals(2)
        self.duration_spin.setSuffix(" sec")
        layout.addRow("Duration:", self.duration_spin)
        
        # Type
        self.type_combo = qw.QComboBox()
        self.type_combo.addItems(['action', 'camera', 'audio', 'event', 'effect'])
        layout.addRow("Type:", self.type_combo)
        
        # Buttons
        button_layout = qw.QHBoxLayout()
        
        self.save_btn = qw.QPushButton("Save Changes")
        self.save_btn.clicked.connect(self.save_changes)
        button_layout.addWidget(self.save_btn)
        
        self.cancel_btn = qw.QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_changes)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addRow(button_layout)
        
        self.setLayout(layout)
        self.setEnabled(False)  # Disabled until clip is loaded
        
    def load_clip(self, clip):
        """Load clip data into the form"""
        self.current_clip = clip
        
        if clip:
            self.name_edit.setText(getattr(clip, 'name', ''))
            self.start_spin.setValue(getattr(clip, 'start_time', 0.0))
            self.duration_spin.setValue(getattr(clip, 'duration', 1.0))
            
            clip_type = getattr(clip, 'type', 'action')
            index = self.type_combo.findText(clip_type)
            if index >= 0:
                self.type_combo.setCurrentIndex(index)
                
            self.setEnabled(True)
        else:
            self.clear()
            
    def save_changes(self):
        """Apply changes to the clip"""
        if not self.current_clip:
            return
            
        # Update clip properties
        self.current_clip.name = self.name_edit.text()
        self.current_clip.start_time = self.start_spin.value()
        self.current_clip.duration = self.duration_spin.value()
        self.current_clip.type = self.type_combo.currentText()
        
        self.clip_modified.emit()
        qw.QMessageBox.information(self, "Saved", "Clip changes saved!")
        
    def cancel_changes(self):
        """Reload original clip data"""
        self.load_clip(self.current_clip)
        
    def clear(self):
        """Clear the form"""
        self.name_edit.clear()
        self.start_spin.setValue(0.0)
        self.duration_spin.setValue(1.0)
        self.type_combo.setCurrentIndex(0)
        self.setEnabled(False)


class AddClipDialog(qw.QDialog):
    """Dialog for adding a new clip"""
    
    def __init__(self, timeline, parent=None):
        super().__init__(parent)
        self.timeline = timeline
        self.setWindowTitle("Add Clip")
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize the dialog UI"""
        layout = qw.QFormLayout()
        
        # Name
        self.name_edit = qw.QLineEdit()
        self.name_edit.setPlaceholderText("Enter clip name")
        layout.addRow("Name:", self.name_edit)
        
        # Start time
        self.start_spin = qw.QDoubleSpinBox()
        self.start_spin.setRange(0.0, 9999.0)
        self.start_spin.setDecimals(2)
        self.start_spin.setSuffix(" sec")
        layout.addRow("Start Time:", self.start_spin)
        
        # Duration
        self.duration_spin = qw.QDoubleSpinBox()
        self.duration_spin.setRange(0.01, 9999.0)
        self.duration_spin.setDecimals(2)
        self.duration_spin.setSuffix(" sec")
        self.duration_spin.setValue(1.0)
        layout.addRow("Duration:", self.duration_spin)
        
        # Type
        self.type_combo = qw.QComboBox()
        self.type_combo.addItems(['action', 'camera', 'audio', 'event', 'effect'])
        layout.addRow("Type:", self.type_combo)
        
        # Buttons
        buttons = qw.QDialogButtonBox(
            qw.QDialogButtonBox.Ok | qw.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
        self.setLayout(layout)
        
    def accept(self):
        """Create the new clip and add to timeline"""
        if not self.name_edit.text():
            qw.QMessageBox.warning(self, "Invalid Name", "Please enter a clip name.")
            return
            
        # Create new clip object (this depends on evfl library structure)
        # For now, we'll create a simple object
        from types import SimpleNamespace
        
        new_clip = SimpleNamespace(
            name=self.name_edit.text(),
            start_time=self.start_spin.value(),
            duration=self.duration_spin.value(),
            type=self.type_combo.currentText(),
            actor_identifier=None,
            parameters={}
        )
        
        # Add to timeline
        clips = getattr(self.timeline, 'clips', [])
        clips.append(new_clip)
        
        super().accept()
