"""

module docstring here
"""

from PySide2 import QtCore, QtWidgets, QtGui
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya import cmds
from . import checker
from . import framelayout
reload(checker)
reload(framelayout)


class Separator(QtWidgets.QWidget):

    def __init__(self, category="", parent=None):
        super(Separator, self).__init__(parent)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Expanding)
        label = QtWidgets.QLabel("  " + category)
        font = QtGui.QFont()
        font.setItalic(True)
        font.setCapitalization(QtGui.QFont.AllUppercase)
        font.setBold(True)
        label.setFont(font)
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(line)
        layout.addWidget(label)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)


class CheckerWidget(QtWidgets.QWidget):

    def __init__(self, chk, settings=None):
        # type: (checker.BaseChecker)
        super(CheckerWidget, self).__init__()

        self.checker = chk
        self.settings = settings
        self.createUI()

    def createUI(self):
        layout = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.LeftToRight)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(QtCore.Qt.AlignTop)

        self.frame = framelayout.FrameLayout(self.checker.name)
        if not self.checker.isEnabled:
            self.setEnabled(False)

        self.checkButton = QtWidgets.QPushButton("Check")
        # self.checkButton.setSizePolicy(
        #     QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Expanding)
        self.checkButton.clicked.connect(self.check)
        self.fixButton = QtWidgets.QPushButton("Fix")
        self.fixButton.clicked.connect(self.fix)
        if self.checker.isFixable is not True:
            self.fixButton.setEnabled(False)

        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.addWidget(self.checkButton)
        buttonLayout.addWidget(self.fixButton)

        self.errorList = QtWidgets.QListWidget()
        self.errorList.itemClicked.connect(self.errorSelected)

        self.frame.addWidget(self.errorList)
        self.frame.addLayout(buttonLayout)

        layout.addWidget(self.frame)

        self.setLayout(layout)

    def check(self, path=None):
        if not self.checker.isEnabled:
            return

        if path is None:
            sel = cmds.ls(sl=True, fl=True, long=True)
            if not sel:
                cmds.warning("Nothing is selected")
                return
            path = sel[0]

        children = cmds.listRelatives(
            path, children=True, ad=True, fullPath=True, type="transform") or []
        children.append(path)

        self.doCheck(children)

    def doCheck(self, objs):

        # Clear list items
        self.errorList.clear()

        errs = self.checker.checkIt(objs, self.settings)

        if errs:
            for err in errs:
                self.errorList.addItem(err)
                if self.checker.isWarning:
                    self.frame.setStatusIcon("warning")
                else:
                    self.frame.setStatusIcon("bad")
        else:
            self.frame.setStatusIcon("good")

    def fix(self):
        if not self.checker.isEnabled:
            return

        self.checker.fixIt()

        # Re-check
        self.check()

    def errorSelected(self, *args):
        """
        Select error components

        """

        err = args[0]
        if err.components is None:
            cmds.select(err.longName, r=True)
        else:
            cmds.select(err.components, r=True)


class Settings(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(Settings, self).__init__(parent)

        self.createUI()

    def createUI(self):

        self.maxFaceArea = QtWidgets.QLineEdit("0.000001")

        layout = QtWidgets.QGridLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
        layout.addWidget(QtWidgets.QLabel("Max face area"), 0, 0)
        layout.addWidget(self.maxFaceArea, 0, 1)
        self.setLayout(layout)

    def getSettings(self):

        data = {
            "maxFaceArea": float(self.maxFaceArea.text())
        }

        return data


class ModelSanityChecker(QtWidgets.QWidget):
    """ Main sanity checker class """

    def __init__(self, settings=None, parent=None):
        super(ModelSanityChecker, self).__init__(parent)

        checkerObjs = [i() for i in checker.CHECKERS]
        checkerObjs.sort()
        self.checkerWidgets = [CheckerWidget(i, settings) for i in checkerObjs]
        self.createUI()


    def createUI(self):
        """
        GUI method

        """

        mainLayout = QtWidgets.QVBoxLayout()
        mainLayout.setContentsMargins(0, 0, 0, 0)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(1)

        scrollLayout = QtWidgets.QVBoxLayout()
        currentCategory = self.checkerWidgets[0].checker.category
        scrollLayout.addWidget(Separator(currentCategory))
        for widget in self.checkerWidgets:
            if currentCategory != widget.checker.category:
                cat = widget.checker.category
                currentCategory = cat
                scrollLayout.addWidget(Separator(cat))
            scrollLayout.addWidget(widget)

        content = QtWidgets.QWidget()
        content.setLayout(scrollLayout)

        scroll.setWidget(content)

        self.rootLE = QtWidgets.QLineEdit()
        setButton = QtWidgets.QPushButton("Set Selected")
        setButton.clicked.connect(self.setSelected)

        checkAllButton = QtWidgets.QPushButton("Check All")
        checkAllButton.clicked.connect(self.checkAll)

        fixAllButton = QtWidgets.QPushButton("Fix All")
        fixAllButton.clicked.connect(self.fixAll)

        rootLayout = QtWidgets.QHBoxLayout()
        rootLayout.addWidget(self.rootLE)
        rootLayout.addWidget(setButton)

        mainLayout.addLayout(rootLayout)
        mainLayout.addWidget(scroll)
        mainLayout.addWidget(checkAllButton)
        mainLayout.addWidget(fixAllButton)

        self.setLayout(mainLayout)

    def setSelected(self):
        sel = cmds.ls(sl=True, fl=True, long=True)
        if sel:
            root = sel[0]
            self.rootLE.setText(root)

    def checkAll(self):
        """
        Check all

        """

        node = self.rootLE.text()

        progDialog = QtWidgets.QProgressDialog(
            "Now Checking...",
            "Cancel",
            0,
            len(self.checkerWidgets),
            self)
        progDialog.setWindowTitle("Building library")
        # progDialog.setWindowModality(QtCore.Qt.WindowModal)
        progDialog.show()

        for num, widget in enumerate(self.checkerWidgets):
            if node == "":
                widget.check()
            else:
                widget.check(node)

            progDialog.setValue(num+1)
            progDialog.setLabel(
                QtWidgets.QLabel(r'Now checking "{}"'.format(widget.checker.name)))
            QtCore.QCoreApplication.processEvents()

        progDialog.close()

    def fixAll(self):
        """
        Fix all

        """

        for widget in self.checkerWidgets:
            widget.fix()


class CentralWidget(QtWidgets.QWidget):
    """ Central widget """

    def __init__(self, parent=None):
        """ Init """

        super(CentralWidget, self).__init__(parent)

        self.createUI()
        self.layoutUI()

    def createUI(self):
        """ Crete widgets """

        settings = Settings(self)
        checker = ModelSanityChecker(settings, self)

        self.tabWidget = QtWidgets.QTabWidget()
        self.tabWidget.addTab(checker, "SanityChecker")
        self.tabWidget.addTab(settings, "Settings")

    def layoutUI(self):
        """ Layout widgets """

        mainLayout = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.TopToBottom)
        mainLayout.setContentsMargins(5, 5, 5, 5)
        mainLayout.addWidget(self.tabWidget)

        self.setLayout(mainLayout)



class MainWindow(MayaQWidgetDockableMixin, QtWidgets.QMainWindow):
    """
    Main window

    """

    def __init__(self, parent=None):
        """ init """

        super(MainWindow, self).__init__(parent)

        self.thisObjectName = "sanityCheckerWindow"
        self.winTitle = "Sanity Checker"
        self.workspaceControlName = self.thisObjectName + "WorkspaceControl"

        self.setObjectName(self.thisObjectName)
        self.setWindowTitle(self.winTitle)

        self.setWindowFlags(QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        # Create and set central widget
        self.cWidget = CentralWidget()
        self.setCentralWidget(self.cWidget)

        self.setupMenu()

    def setupMenu(self):
        """ Setup menu """

        menu = self.menuBar()

        # About
        aboutAction = QtWidgets.QAction("&About", self)
        aboutAction.setStatusTip('About this script')
        aboutAction.triggered.connect(self.showAbout)

        menu.addAction("File")
        helpMenu = menu.addMenu("&Help")
        helpMenu.addAction(aboutAction)

    def showAbout(self):
        """
        About message
        """

        QtWidgets.QMessageBox.about(self, 'About ', 'test\n')

    def run(self):
        try:
            cmds.deleteUI(self.workspaceControlName)
        except RuntimeError:
            pass

        self.show(dockable=True)
        cmds.workspaceControl(
            self.workspaceControlName,
            edit=True,
            initialWidth=270,
            minimumWidth=270,
            dockToControl=['Outliner', 'right'])
        self.raise_()


def main():

    window = MainWindow()
    window.run()


if __name__ == "__main__":
    main()
