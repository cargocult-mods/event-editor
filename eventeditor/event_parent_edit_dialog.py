from enum import IntEnum, auto
import typing

from eventeditor.flow_data import FlowData, FlowDataChangeReason
import eventeditor.util as util
from evfl import Event, ActionEvent, SwitchEvent, ForkEvent, JoinEvent, SubFlowEvent
from evfl.common import RequiredIndex
import PyQt5.QtCore as qc # type: ignore
import PyQt5.QtWidgets as q # type: ignore


class ParentLinkType(IntEnum):
	Next = 0
	SwitchCase = auto()
	ForkBranch = auto()


class ParentLink:
	__slots__ = ('parent', 'link_type', 'detail')
	def __init__(self, parent: Event, link_type: ParentLinkType, detail: typing.Optional[int] = None) -> None:
		self.parent = parent
		self.link_type = link_type
		# detail is used for SwitchCase value; ignored for others
		self.detail = detail

	def __eq__(self, other) -> bool:
		if not isinstance(other, ParentLink):
			return False
		return self.parent == other.parent and self.link_type == other.link_type and self.detail == other.detail


class ParentLinkModelColumn(IntEnum):
	Parent = 0
	Link = auto()


class ParentLinkModel(qc.QAbstractTableModel):
	def __init__(self, parent, links: typing.List[ParentLink]) -> None:
		super().__init__(parent)
		self.l: typing.List[ParentLink] = list(links)

	def isValid(self) -> bool:
		# Ensure switch case values are unique per switch parent in this model
		switch_seen: typing.Set[typing.Tuple[Event, int]] = set()
		for pl in self.l:
			if pl.link_type == ParentLinkType.SwitchCase:
				key = (pl.parent, typing.cast(int, pl.detail))
				if key in switch_seen:
					return False
				switch_seen.add(key)
		return True

	def rowCount(self, parent) -> int:
		return len(self.l)

	def columnCount(self, parent) -> int:
		return len(ParentLinkModelColumn)

	def flags(self, index: qc.QModelIndex) -> qc.Qt.ItemFlags:
		# Read-only cells; use Add/Remove controls to modify model
		return super().flags(index)

	def headerData(self, section, orientation, role) -> qc.QVariant:
		if role != qc.Qt.DisplayRole:
			return qc.QVariant()
		if section == ParentLinkModelColumn.Parent:
			return 'Parent event'
		if section == ParentLinkModelColumn.Link:
			return 'Link'
		return 'Unknown'

	def data(self, index: qc.QModelIndex, role) -> typing.Any:
		row = index.row()
		col = index.column()
		pl = self.l[row]
		if role == qc.Qt.UserRole:
			return pl
		if role == qc.Qt.DisplayRole or role == qc.Qt.ToolTipRole:
			if col == ParentLinkModelColumn.Parent:
				return util.get_event_full_description(pl.parent)
			if col == ParentLinkModelColumn.Link:
				if pl.link_type == ParentLinkType.Next:
					return 'Next'
				if pl.link_type == ParentLinkType.ForkBranch:
					return 'Fork branch'
				if pl.link_type == ParentLinkType.SwitchCase:
					return f'Switch case = {pl.detail}'
		return qc.QVariant()

	def appendLink(self, link: ParentLink) -> bool:
		# Prevent exact duplicates
		if any(link == existing for existing in self.l):
			q.QMessageBox.critical(None, 'Invalid data', 'This parent link already exists.')
			return False
		self.beginInsertRows(qc.QModelIndex(), len(self.l), len(self.l))
		self.l.append(link)
		self.endInsertRows()
		return True

	def removeRow(self, row: int) -> bool:
		self.beginRemoveRows(qc.QModelIndex(), row, row)
		self.l.pop(row)
		self.endRemoveRows()
		return True


class EditParentsDialog(q.QDialog):
	def __init__(self, parent, child_event: Event, flow_data: FlowData) -> None:
		super().__init__(parent)
		self.setWindowTitle('Edit parents')
		self.setMinimumWidth(700)
		self.flow_data = flow_data
		self.child_event = child_event

		self.model = ParentLinkModel(self, self._gatherExistingLinks())

		self.tview = q.QTableView()
		self.tview.setModel(self.model)
		self.tview.verticalHeader().hide()
		self.tview.setSelectionBehavior(q.QAbstractItemView.SelectRows)
		self.tview.setSelectionMode(q.QAbstractItemView.SingleSelection)
		self.tview.horizontalHeader().setSectionResizeMode(q.QHeaderView.ResizeToContents)
		self.tview.horizontalHeader().setSectionResizeMode(1, q.QHeaderView.Stretch)
		self.tview.setContextMenuPolicy(qc.Qt.CustomContextMenu)
		self.tview.customContextMenuRequested.connect(self.onContextMenu)

		add_btn_box = q.QHBoxLayout()
		add_btn = q.QPushButton('Add parent...')
		add_btn.clicked.connect(self.addParent)
		add_btn_box.addStretch()
		add_btn_box.addWidget(add_btn)

		btn_box = q.QDialogButtonBox(q.QDialogButtonBox.Save | q.QDialogButtonBox.Cancel)
		btn_box.accepted.connect(self.accept)
		btn_box.rejected.connect(self.reject)

		layout = q.QVBoxLayout(self)
		layout.addWidget(self.tview)
		layout.addLayout(add_btn_box)
		layout.addWidget(btn_box)

	def _gatherExistingLinks(self) -> typing.List[ParentLink]:
		links: typing.List[ParentLink] = []
		flow = self.flow_data.flow
		if not flow or not flow.flowchart:
			return links
		for e in flow.flowchart.events:
			data = e.data
			if isinstance(data, (ActionEvent, JoinEvent, SubFlowEvent)):
				if data.nxt.v == self.child_event:
					links.append(ParentLink(e, ParentLinkType.Next))
			elif isinstance(data, SwitchEvent):
				for value, case in data.cases.items():
					if case.v == self.child_event:
						links.append(ParentLink(e, ParentLinkType.SwitchCase, value))
			elif isinstance(data, ForkEvent):
				for fork in data.forks:
					if fork.v == self.child_event:
						links.append(ParentLink(e, ParentLinkType.ForkBranch))
		return links

	def onContextMenu(self, pos) -> None:
		smodel = self.tview.selectionModel()
		if not smodel.hasSelection():
			return
		sidx = smodel.selectedRows()[0]
		menu = q.QMenu()
		menu.addAction('Remove', lambda: self.model.removeRow(sidx.row()))
		menu.exec_(self.sender().viewport().mapToGlobal(pos))

	def addParent(self) -> None:
		# Lazy import to avoid cycles
		from eventeditor.event_chooser_dialog import EventChooserDialog
		dialog = EventChooserDialog(self, self.flow_data, enable_ctx_menu=False)
		if not dialog.exec_():
			return
		selected = dialog.getSelectedEvent()
		if selected == self.child_event:
			q.QMessageBox.critical(self, 'Invalid choice', 'Cannot set an event as a parent of itself.')
			return
		# Determine link type and details
		if isinstance(selected.data, (ActionEvent, JoinEvent, SubFlowEvent)):
			self.model.appendLink(ParentLink(selected, ParentLinkType.Next))
		elif isinstance(selected.data, ForkEvent):
			self.model.appendLink(ParentLink(selected, ParentLinkType.ForkBranch))
		elif isinstance(selected.data, SwitchEvent):
			value, ok = q.QInputDialog.getInt(self, 'Add parent', 'Switch case value:')
			if not ok:
				return
			self.model.appendLink(ParentLink(selected, ParentLinkType.SwitchCase, value))
		else:
			q.QMessageBox.critical(self, 'Not supported', 'Unsupported parent event type.')

	def _applyChanges(self) -> bool:
		flow = self.flow_data.flow
		if not flow or not flow.flowchart:
			return False

		# Validation: switch case duplicates per parent (already ensured by model)
		if not self.model.isValid():
			q.QMessageBox.critical(self, 'Invalid data', 'Please ensure there are no duplicate switch cases for the same parent.')
			return False

		# Build quick lookup of desired links per parent
		desired_next: typing.Set[Event] = set()
		desired_switch: typing.Dict[Event, typing.Set[int]] = {}
		desired_fork_count: typing.Dict[Event, int] = {}
		for pl in self.model.l:
			if pl.link_type == ParentLinkType.Next:
				desired_next.add(pl.parent)
			elif pl.link_type == ParentLinkType.SwitchCase:
				assert pl.detail is not None
				desired_switch.setdefault(pl.parent, set()).add(int(pl.detail))
			elif pl.link_type == ParentLinkType.ForkBranch:
				desired_fork_count[pl.parent] = desired_fork_count.get(pl.parent, 0) + 1

		# Confirmation if we will overwrite existing next pointers
		to_overwrite = []
		for parent in desired_next:
			data = parent.data
			if isinstance(data, (ActionEvent, JoinEvent, SubFlowEvent)):
				if data.nxt.v and data.nxt.v is not self.child_event:
					to_overwrite.append(parent)
		if to_overwrite:
			names = '\n'.join(e.name for e in to_overwrite)
			ret = q.QMessageBox.question(self, 'Overwrite links', f'This will overwrite the child link of the following events to point to {self.child_event.name}:\n\n{names}\n\nContinue?')
			if ret != q.QMessageBox.Yes:
				return False

		# Apply removals and additions per parent type
		for e in flow.flowchart.events:
			data = e.data
			if isinstance(data, (ActionEvent, JoinEvent, SubFlowEvent)):
				if e in desired_next:
					data.nxt.v = self.child_event
				elif data.nxt.v == self.child_event:
					data.nxt.v = None
			elif isinstance(data, SwitchEvent):
				desired_cases = desired_switch.get(e, set())
				# Remove or redirect existing cases that target child
				for value in list(data.cases.keys()):
					if data.cases[value].v == self.child_event and value not in desired_cases:
						del data.cases[value]
				# Add desired cases
				for value in desired_cases:
					# Prevent overwriting cases pointing to other events
					if value in data.cases and data.cases[value].v is not self.child_event:
						q.QMessageBox.critical(self, 'Conflict', f'Switch event {e.name} already has a case for value {value} pointing elsewhere.')
						return False
					if value not in data.cases:
						ri: RequiredIndex[Event] = RequiredIndex()
						ri.v = self.child_event
						data.cases[value] = ri
			elif isinstance(data, ForkEvent):
				# Count existing forks targeting child
				current = [fork for fork in data.forks if fork.v == self.child_event]
				desired = desired_fork_count.get(e, 0)
				if desired < len(current):
					# Remove extras
					remaining = desired
					new_forks = []
					for fork in data.forks:
						if fork.v != self.child_event:
							new_forks.append(fork)
						elif remaining > 0:
							new_forks.append(fork)
							remaining -= 1
					data.forks = new_forks
				elif desired > len(current):
					# Add missing forks
					for _ in range(desired - len(current)):
						ri = RequiredIndex[Event]()
						ri.v = self.child_event
						data.forks.append(ri)

		return True

	def accept(self) -> None:
		if not self._applyChanges():
			return
		self.flow_data.flowDataChanged.emit(FlowDataChangeReason.Events)
		super().accept()