import os
from PyQt6.QtWidgets import QVBoxLayout, QFrame, QLabel, QSizePolicy, QWidget, QTreeWidget, QTreeWidgetItem
from PyQt6 import QtGui
from pathlib import Path
import re

CACHE_LOCATION = os.path.join(os.path.dirname(__file__), "../temp/cache")


class Query(QTreeWidgetItem):
	"""Custom item for the query tree"""
	def __init__(self, name, path):
		super().__init__([name])
		self.name = name
		self.path = path
		self.verified = False


class Property(QTreeWidgetItem):
	"""Custom item for the property tree"""
	def __init__(self, name, path):
		super().__init__([name, "Pending"])
		self.name = name
		self.path = path
		self.queries = []
		self._verified = False

	def add_query(self, query):
		self.queries.append(query)
		self.addChild(QTreeWidgetItem([query.name]))

	@property
	def verified(self):
		return self._verified
	
	@verified.setter
	def verified(self, value):
		self._verified = value
		self.setForeground(0, QtGui.QColor("black"))
		self.setForeground(1, QtGui.QColor("black"))

		if value is True:
			self.setBackground(0, QtGui.QColor(200, 255, 200)) 
			self.setBackground(1, QtGui.QColor(200, 255, 200))
			self.setText(1, "True")
		elif value is False:
			self.setBackground(0, QtGui.QColor(255, 200, 200))
			self.setBackground(1, QtGui.QColor(255, 200, 200))
			self.setText(1, "False") 
		else:
			self.setText(1, "Unknown")


class HeirarchicalOutput(QTreeWidget):
	"""Custom output area storing the structure of the VCL cache"""
	def __init__(self, parent=None, cache_location=CACHE_LOCATION):
		super().__init__(parent)
		self.cache_location = Path(cache_location)
		self.properties = {}

		self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
		self.setColumnCount(2)
		self.setHeaderLabels(["Property", "Result", "Counter Example"])
		self.setColumnWidth(0, 300)
		self.setColumnWidth(1, 100)

		self.parse_cache()

		for prop in self.properties.values():
			self.addTopLevelItem(prop)

		self.update_verification()


	def parse_cache(self):
		"""Parse the cache directory and create a mapping of properties to queries"""
		glob_pattern = "property*.vcl-plan"
		files = list(self.cache_location.glob(glob_pattern))
		sort_key = lambda p: int(re.findall(r"(\d+)", p.stem)[-1])
		files.sort(key=sort_key)

		for file in files:
			self.properties[file.stem] = Property(file.stem, file)

		for prop in self.properties.values():
			glob_pattern = f"{prop.name}-query*.txt"
			files = list(self.cache_location.glob(glob_pattern))
			files.sort(key=sort_key)
			for file in files:
				query = Query(file.stem, file)
				prop.add_query(query)


	def update_verification(self):
		glob_pattern = "property*.vcl-result"
		files = list(self.cache_location.glob(glob_pattern))
		for file in files:
			prop_name = file.stem
			try:
				with open(file.absolute(), "r") as f:
					value = f.read().strip() == "True"
					self.properties[prop_name].verified = value
			except Exception as e:
				print(f"Error reading file {file}: {e}")
				self.properties[prop_name].setText(1, "Error")
				self.properties[prop_name].setBackground(0, QtGui.QColor("orange"))

			
		