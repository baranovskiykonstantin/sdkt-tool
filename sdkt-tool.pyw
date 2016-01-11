#!/usr/bin/env python2
# -*-    Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4    -*-
### BEGIN LICENSE
# Copyright (C) 2013 Baranovskiy Konstantin (baranovskiykonstantin@gmail.com)
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

import sys
import time
import os.path
import csv, codecs, cStringIO

from PyQt4 import QtCore, QtGui, QtSvg, uic

from USBDevice import *


VERSION = 1.0


class MainWindow(QtGui.QMainWindow):
    """
    Main window based on Qt widgets.

    """

    def __init__(self, parent=None):
        """
        Initialization of the main window.

        """
        QtGui.QMainWindow.__init__(self, parent)
        uic.loadUi('gui/main_window.ui', self)

        self.skip_checked_signal = False
        self.addr_to_treeitem = {}
        self.addr_is_set = False

        self.treewidget.header().setMovable(False)

        # Load settings
        self.settings = QtCore.QSettings("settings.ini", QtCore.QSettings.IniFormat)

        self.settings.beginGroup("mainwindow")
        self.resize(self.settings.value("size", QtCore.QSize(850, 550)).toSize())
        self.move(self.settings.value("pos", QtCore.QPoint(100, 100)).toPoint())
        if self.settings.value("maximized", "false").toBool():
            self.setWindowState(self.windowState() | QtCore.Qt.WindowMaximized)
        else:
            self.setWindowState(self.windowState() & ~QtCore.Qt.WindowMaximized)
        self.settings.endGroup()

        self.settings.beginGroup("treewidget")
        for column in range(self.treewidget.header().count()):
            width = self.settings.value("column{}".format(column), 200).toInt()[0]
            self.treewidget.header().resizeSection(column, width)
        self.settings.endGroup()

        self.ref_lineedit.setText(self.settings.value("ref/value", "60.4").toString())
        self.addr_spinbox.setValue(self.settings.value("addr/value", "1").toInt()[0])

        if self.settings.value("error/absolute", "true").toBool():
            self.treewidget.headerItem().setText(3, u"Погрешность, Ом")
        else:
            self.treewidget.headerItem().setText(3, u"Погрешность, %")

        self.progressbar.hide()

        for top in range(self.treewidget.topLevelItemCount()):
            for child in range(self.treewidget.topLevelItem(top).childCount()):
                self.calculate_error(top, child)
                for column in range(1, self.treewidget.topLevelItem(top).child(child).columnCount()):
                    self.treewidget.topLevelItem(top).child(child).setTextAlignment(column, QtCore.Qt.AlignHCenter)

        self.ref_lineedit.setValidator(QtGui.QDoubleValidator(0, 1, 3))

        self.measurement = Measurement()
        self.connect(self.measurement, QtCore.SIGNAL('result(int, float)'), self.on_measurement_result)
        self.connect(self.measurement, QtCore.SIGNAL('finished()'), self.on_measurement_finished)
        self.connect(self.measurement, QtCore.SIGNAL('error(QString, QString)'), self.on_measurement_error)

        self.periodical_mesurement = QtCore.QTimer(self)
        self.periodical_mesurement.setInterval(1000)
        self.connect(self.periodical_mesurement, QtCore.SIGNAL('timeout()'), self.on_periodical_measurement)

    def calculate_error(self, top, child):
        """
        Calculate error between ref and measured values.

        """
        ref = float(self.treewidget.topLevelItem(top).child(child).text(1))
        measured = float(self.treewidget.topLevelItem(top).child(child).text(2))
        error = 0
        if self.settings.value("error/absolute", "true").toBool():
            error = measured - ref
            if abs(error) < self.settings.value("error/level", "1.0").toFloat()[0]:
                self.treewidget.topLevelItem(top).child(child).setTextColor(
                        3,
                        QtGui.QColor(self.settings.value("error/color_norm", "green").toString())
                        )
            else:
                self.treewidget.topLevelItem(top).child(child).setTextColor(
                        3,
                        QtGui.QColor(self.settings.value("error/color_error", "red").toString())
                        )
        else:
            if ref == 0:
                error = "???"
                self.treewidget.topLevelItem(top).child(child).setTextColor(
                        3,
                        QtGui.QColor("blue")
                        )
                self.treewidget.topLevelItem(top).child(child).setText(3, error)
                return

            error = (abs(ref-measured) / ref) * 100
            if error < self.settings.value("error/level", "1.0").toFloat()[0]:
                self.treewidget.topLevelItem(top).child(child).setTextColor(
                        3,
                        QtGui.QColor(self.settings.value("error/color_norm", "green").toString())
                        )
            else:
                self.treewidget.topLevelItem(top).child(child).setTextColor(
                        3,
                        QtGui.QColor(self.settings.value("error/color_error", "red").toString())
                        )
        error = self.float_to_str(error)
        self.treewidget.topLevelItem(top).child(child).setText(3, error)

    def float_to_str(self, value):
        """
        Convert float value to string and remove leading zeros.

        """
        string = '{:0.3f}'.format(value)
        string = string.rstrip('0')
        string = string.rstrip('.')
        return string

    @QtCore.pyqtSlot(QtGui.QTreeWidgetItem, int)
    def on_treewidget_itemChanged(self, item, column):
        """
        Processing checked states.

        """
        if self.skip_checked_signal:
            return

        self.skip_checked_signal = True
        # Top level item
        if item.parent():
            state = 0
            for child in range(item.parent().childCount()):
                state += item.parent().child(child).checkState(0)
            if state:
                if state == item.parent().childCount() * 2:
                    state = QtCore.Qt.Checked
                else:
                    state = QtCore.Qt.PartiallyChecked
            else:
                state = QtCore.Qt.Unchecked
            item.parent().setCheckState(0, state)
        else:
            state = item.checkState(0)
            for child in range(item.childCount()):
                item.child(child).setCheckState(0, state)
        self.skip_checked_signal = False

    @QtCore.pyqtSlot(QtGui.QTreeWidgetItem, int)
    def on_treewidget_itemDoubleClicked(self, item, column):
        """
        Set addres in SDKT device for selected point.

        """
        def wait():
            """
            Wait untill the command is executed.

            """
            for i in range(10):
                time.sleep(0.1)
                if sdkt_device.getControlMsg(1) == 0:
                    return
            else:
                QtGui.QMessageBox.critical(
                        self,
                        u"SDKT device",
                        u"Устройство не отвечает!\n" \
                        u"Превышено время ожидания ответа."
                        )
                sdkt_device.close()
                return

        if item.parent():
            top = self.treewidget.indexOfTopLevelItem(item.parent())
            if (top < 12) or (top == 13):
                sensor_addr = item.text(4)
                sensor_addr = int(sensor_addr.split(' ')[0])
                pcb_addr = self.addr_spinbox.value()
                gnd_num = int(item.text(9))
                addr = pcb_addr*1024 + gnd_num*128 + sensor_addr
                try:
                    sdkt_device = USBDeviceCustom()
                    if sdkt_device.find():
                        sdkt_device.open()
                    else:
                        QtGui.QMessageBox.critical(
                                self,
                                u"SDKT device",
                                u"Устройство не подключено или неисправно!"
                                )
                        return
                    sdkt_device.setControlMsg(2, addr)
                    wait()
                    sdkt_device.setControlMsg(1, 2)
                    wait()
                    self.addr_is_set = True
                    self.addr_to_treeitem = {}
                    self.addr_to_treeitem[sensor_addr] = (top, self.treewidget.topLevelItem(top).indexOfChild(item))
                    self.periodical_mesurement.start()
                except Exception, error:
                    self.addr_is_set = False
                    QtGui.QMessageBox.critical(
                            self,
                            u"SDKT device",
                            str(error)
                            )

    @QtCore.pyqtSlot(QtGui.QTreeWidgetItem, int)
    def on_treewidget_itemPressed(self, item, column):
        """
        If address was set by double clicking - reset it.

        """
        if self.addr_is_set:
            self.addr_is_set = False
            self.periodical_mesurement.stop()
            try:
                sdkt_device = USBDeviceCustom()
                if sdkt_device.find():
                    sdkt_device.open()
                else:
                    QtGui.QMessageBox.critical(
                            self,
                            u"SDKT device",
                            u"Устройство не подключено или неисправно!"
                            )
                    return
                sdkt_device.setControlMsg(1, 1)
            except Exception, error:
                QtGui.QMessageBox.critical(
                        self,
                        u"SDKT device",
                        str(error)
                        )

    @QtCore.pyqtSlot()
    def on_ref_pushbutton_clicked(self):
        """
        Set value of ref resistance for selected target.

        """
        top_index = self.treewidget.indexOfTopLevelItem(self.treewidget.currentItem().parent())
        if top_index < 13:
            value = self.ref_lineedit.text()
            if not value:
                value = '0'
            if self.ref_choice1_radiobutton.isChecked():
                if self.treewidget.currentItem().parent():
                    self.treewidget.currentItem().setText(1, value)
                    top_index = self.treewidget.indexOfTopLevelItem(self.treewidget.currentItem().parent())
                    child_index = self.treewidget.topLevelItem(top_index).indexOfChild(self.treewidget.currentItem())
                    self.calculate_error(top_index, child_index)
            if self.ref_choice2_radiobutton.isChecked():
                top = self.treewidget.currentItem().parent()
                if top:
                    top_index = self.treewidget.indexOfTopLevelItem(top)
                    for child in range(top.childCount()):
                        top.child(child).setText(1, value)
                        self.calculate_error(top_index, child)
            if self.ref_choice3_radiobutton.isChecked():
                for top in range(12):
                    for child in range(6):
                        self.treewidget.topLevelItem(top).child(child).setText(1, value)
                        self.calculate_error(top, child)

    @QtCore.pyqtSlot()
    def on_action_export_triggered(self):
        """
        Save selected lines ot *.csv file.

        """
        last_dir = self.settings.value("export/dir", "").toString().toUtf8()
        last_dir = unicode(last_dir, "utf-8")
        file_name = QtGui.QFileDialog.getSaveFileName(
                self,
                u"Экспорт",
                os.path.join(last_dir, u"Местный блок №{}.csv".format(self.addr_spinbox.value())),
                u"CSV files *.csv (*.csv)"
                ).toUtf8()
        file_name = unicode(file_name, "utf-8")
        csv_file = open(file_name, "wb")
        writer = CsvWriter(csv_file)

        columns = []
        for column in range(1, 12):
            if self.settings.value("export/column{}".format(column), "false").toBool():
                columns.append(column)
        row = [u"Местный блок №{}".format(self.addr_spinbox.value())]
        for column in range(1, 12):
            if self.settings.value("export/column{}".format(column), "false").toBool():
                row.append(self.treewidget.headerItem().text(column))
        writer.writerow(row)

        for top in range(self.treewidget.topLevelItemCount()):
            if self.treewidget.topLevelItem(top).checkState(0) != QtCore.Qt.Unchecked:
                # Empty row for readability
                writer.writerow([])
                writer.writerow([self.treewidget.topLevelItem(top).text(0)])
                for child in range(self.treewidget.topLevelItem(top).childCount()):
                    if self.treewidget.topLevelItem(top).child(child).checkState(0) == QtCore.Qt.Checked:
                        row = [self.treewidget.topLevelItem(top).child(child).text(0)]
                        for column in columns:
                            row.append(self.treewidget.topLevelItem(top).child(child).text(column))
                        writer.writerow(row)

        self.settings.setValue("export/dir", os.path.dirname(file_name))


    @QtCore.pyqtSlot()
    def on_action_start_triggered(self):
        """
        Start measuring.

        """
        if self.start_button.text() == u'Начать измерение':
            self.treewidget.setEnabled(False)
            self.start_button.setText(u'Остановить измерение')
            self.action_start.setText(u'&Остановить измерение')
            self.progressbar.show()
            # Create list of the address of sensors for measuring
            self.addr_to_treeitem = {}
            for top in range(self.treewidget.topLevelItemCount()):
                for child in range(self.treewidget.topLevelItem(top).childCount()):
                    if self.treewidget.topLevelItem(top).child(child).checkState(0) == QtCore.Qt.Checked:
                        sensor_addr = self.treewidget.topLevelItem(top).child(child).text(4)
                        sensor_addr = int(sensor_addr.split(' ')[0])
                        pcb_addr = self.addr_spinbox.value()
                        gnd_num = 0
                        if top < 12:
                            gnd_num = self.treewidget.topLevelItem(top).child(child).text(9)
                            gnd_num = int(gnd_num)
                        addr = pcb_addr*1024 + gnd_num*128 + sensor_addr
                        self.addr_to_treeitem[addr] = (top, child)
            self.measurement.sensors = self.addr_to_treeitem.keys()

            self.progressbar.setMaximum(len(self.measurement.sensors))
            self.measurement.start()
        else:
            self.measurement.terminate()

    @QtCore.pyqtSlot()
    def on_action_settings_triggered(self):
        """
        Edit settings.

        """
        settings_dialog = SettingsDialog(self.settings, self)
        if settings_dialog.exec_() == QtGui.QDialog.Accepted:
            if self.settings.value("error/absolute", "true").toBool():
                self.treewidget.headerItem().setText(3, u"Погрешность, Ом")
            else:
                self.treewidget.headerItem().setText(3, u"Погрешность, %")
            for top in range(self.treewidget.topLevelItemCount()):
                for child in range(self.treewidget.topLevelItem(top).childCount()):
                    self.calculate_error(top, child)

    @QtCore.pyqtSlot()
    def on_action_diagnostics_triggered(self):
        """
        Open diagnostics dialog.

        """
        diagnostics_dialog = DiagnosticsDialog(self)
        diagnostics_dialog.exec_()

    @QtCore.pyqtSlot()
    def on_action_check_all_triggered(self):
        """
        Check all lines in treewidget.

        """
        self.skip_checked_signal = True
        for top in range(self.treewidget.topLevelItemCount()):
            self.treewidget.topLevelItem(top).setCheckState(0, QtCore.Qt.Checked)
            for child in range(self.treewidget.topLevelItem(top).childCount()):
                self.treewidget.topLevelItem(top).child(child).setCheckState(0, QtCore.Qt.Checked)
        self.skip_checked_signal = False

    @QtCore.pyqtSlot()
    def on_action_uncheck_all_triggered(self):
        """
        Uncheck all lines in treewidget.

        """
        self.skip_checked_signal = True
        for top in range(self.treewidget.topLevelItemCount()):
            self.treewidget.topLevelItem(top).setCheckState(0, QtCore.Qt.Unchecked)
            for child in range(self.treewidget.topLevelItem(top).childCount()):
                self.treewidget.topLevelItem(top).child(child).setCheckState(0, QtCore.Qt.Unchecked)
        self.skip_checked_signal = False

    @QtCore.pyqtSlot()
    def on_action_expand_all_triggered(self):
        """
        Expand all lines in treewidget.

        """
        for top in range(self.treewidget.topLevelItemCount()):
            self.treewidget.expandItem(self.treewidget.topLevelItem(top))

    @QtCore.pyqtSlot()
    def on_action_collapse_all_triggered(self):
        """
        Collapse all lines in treewidget.

        """
        for top in range(self.treewidget.topLevelItemCount()):
            self.treewidget.collapseItem(self.treewidget.topLevelItem(top))

    @QtCore.pyqtSlot()
    def on_action_about_triggered(self):
        """
        Shows about dialog.

        """
        QtGui.QMessageBox.about(
            self,
            u'О программе...',
            u'<b>SDKT tool</b><br/>' \
            u'<br/>' \
            u'Тестирование плат местных блоков системы дистанционного ' \
            u'контроля температуры СДКТ-02.<br/>' \
            u'<br/>' \
            u'Версия: {0}<br/>' \
            u'Автор: Барановский Константин<br/>' \
            u'Эл. почта: <a href="mailto:baranovskiykonstantin@gmail.com">' \
            u'baranovskiykonstantin@gmail.com</a><br/>' \
            u''.format(VERSION)
            )

    def on_measurement_result(self, addr, value):
        """
        Get measured value at addr.

        """
        top, child = self.addr_to_treeitem[addr]
        resistance = '0'
        frequency = ''
        if value:
            resistance = 536945.93 / float(value) # 537076.8
            resistance = self.float_to_str(resistance)
            frequency = 1000000 / ((float(value) - 8) * 0.083333)
            frequency = u'f = {} Гц'.format(self.float_to_str(frequency))
        self.treewidget.topLevelItem(top).child(child).setText(2, resistance)
        self.treewidget.topLevelItem(top).child(child).setToolTip(2, frequency)
        self.calculate_error(top, child)
        progress = self.measurement.sensors.index(addr) + 1
        self.progressbar.setValue(progress)

    def on_measurement_finished(self):
        """
        All selected sensors are measured.

        """
        self.start_button.setText(u'Начать измерение')
        self.action_start.setText(u'&Начать измерение')
        self.progressbar.hide()
        self.progressbar.setValue(0)
        self.progressbar.setMaximum(0)
        self.treewidget.setEnabled(True)

    def on_measurement_error(self, title, message):
        """
        Show message box with a description of error.

        """
        QtGui.QMessageBox.critical(self, title, message)

    def on_periodical_measurement(self):
        """
        Periodical measurement the addr of the double clicked item.

        """
        def wait():
            """
            Wait untill the command is executed.

            """
            for i in range(10):
                time.sleep(0.1)
                if sdkt_device.getControlMsg(1) == 0:
                    return
            else:
                QtGui.QMessageBox.critical(
                        self,
                        u"SDKT device",
                        u"Устройство не отвечает!\n" \
                        u"Превышено время ожидания ответа."
                        )
                sdkt_device.close()
                self.periodical_mesurement.stop()
                return

        try:
            sdkt_device = USBDeviceCustom()
            if sdkt_device.find():
                sdkt_device.open()
            else:
                QtGui.QMessageBox.critical(
                        self,
                        u"SDKT device",
                        u"Устройство не подключено или неисправно!"
                        )
                self.periodical_mesurement.stop()
                return
            # Measure the freaquency
            sdkt_device.setControlMsg(1, 3)
            wait()
            value = sdkt_device.getControlMsg(3)
            if value in (0x0000, 0xFFFF):
                value = 0
            addr = self.addr_to_treeitem.keys()[0]
            top, child = self.addr_to_treeitem[addr]
            resistance = '0'
            frequency = ''
            if value:
                resistance = 536945.93 / float(value) # 537076.8
                resistance = self.float_to_str(resistance)
                frequency = 1000000 / ((float(value) - 8) * 0.083333)
                frequency = u'f = {} Гц'.format(self.float_to_str(frequency))
            self.treewidget.topLevelItem(top).child(child).setText(2, resistance)
            self.treewidget.topLevelItem(top).child(child).setToolTip(2, frequency)
            self.calculate_error(top, child)
        except Exception, error:
            self.addr_is_set = False
            self.periodical_mesurement.stop()
            QtGui.QMessageBox.critical(
                    self,
                    u"SDKT device",
                    str(error)
                    )

    def closeEvent(self, event):
        """
        Save parameters of the window before closing.

        """
        self.settings.beginGroup("mainwindow")
        if self.settings.value("save_size", "true").toBool():
            self.settings.setValue("save_size", "true")
            if self.isMaximized():
                self.settings.setValue("maximized", "true")
            else:
                self.settings.setValue("maximized", "false")
                self.settings.setValue("size", self.size())
                self.settings.setValue("pos", self.pos())
        else:
            self.settings.setValue("save_size", "false")
            self.settings.remove("maximized")
            self.settings.remove("size")
            self.settings.remove("pos")
        self.settings.endGroup()

        self.settings.beginGroup("treewidget")
        if self.settings.value("save_width", "true").toBool():
            self.settings.setValue("save_width", "true")
            for column in range(12):
                width = self.treewidget.header().sectionSize(column)
                self.settings.setValue("column{}".format(column), width)
        else:
            self.settings.setValue("save_width", "false")
            for column in range(12):
                self.settings.remove("column{}".format(column))
        self.settings.endGroup()

        self.settings.beginGroup("ref")
        if self.settings.value("save_value", "true").toBool():
            self.settings.setValue("save_value", "true")
            self.settings.setValue("value", self.ref_lineedit.text())
        else:
            self.settings.setValue("save_value", "false")
            self.settings.remove("value")
        self.settings.endGroup()


        self.settings.beginGroup("addr")
        if self.settings.value("save_value", "true").toBool():
            self.settings.setValue("save_value", "true")
            self.settings.setValue("value", self.addr_spinbox.value())
        else:
            self.settings.setValue("save_value", "false")
            self.settings.remove("value")
        self.settings.endGroup()


class SettingsDialog(QtGui.QDialog):
    """
    Dialog for editing the settings of SDKT tool.

    """

    def __init__(self, settings, parent=None):
        """
        Initializing of the settings dialog.

        """
        QtGui.QDialog.__init__(self, parent)
        uic.loadUi('gui/settings_dialog.ui', self)

        self.settings = settings

        self.save_size_checkbox.setChecked(
                self.settings.value("mainwindow/save_size", "true").toBool()
                )
        self.save_width_checkbox.setChecked(
                self.settings.value("treewidget/save_width", "true").toBool()
                )
        self.save_ref_checkbox.setChecked(
                self.settings.value("ref/save_value", "true").toBool()
                )
        self.save_addr_checkbox.setChecked(
                self.settings.value("addr/save_value", "true").toBool()
                )

        self.settings.beginGroup("error")
        if self.settings.value("absolute", "true").toBool():
            self.abs_radiobutton.setChecked(True)
        else:
            self.rel_radiobutton.setChecked(True)
        self.error_level_doublespinbox.setValue(
                self.settings.value("level", "1.0").toFloat()[0]
                )
        color_norm = self.settings.value("color_norm", "green").toString()
        self.color_norm_button.setToolTip(color_norm)
        self.color_norm_button.setStyleSheet("QPushButton {{ background-color: {}}}".format(color_norm))
        color_error = self.settings.value("color_error", "red").toString()
        self.color_error_button.setToolTip(color_error)
        self.color_error_button.setStyleSheet("QPushButton {{ background-color: {}}}".format(color_error))
        self.settings.endGroup()

        self.settings.beginGroup("export")
        for column in range(1, 12):
            getattr(self, "column{}_checkbox".format(column)).setChecked(
                        self.settings.value("column{}".format(column)).toBool()
                        )
        self.settings.endGroup()

    @QtCore.pyqtSlot()
    def on_buttonbox_accepted(self):
        """
        Save settings.

        """
        self.settings.setValue(
                "mainwindow/save_size",
                self.save_size_checkbox.isChecked()
                )
        self.settings.setValue(
                "treewidget/save_width",
                self.save_width_checkbox.isChecked()
                )
        self.settings.setValue(
                "ref/save_value",
                self.save_ref_checkbox.isChecked()
                )
        self.settings.setValue(
                "addr/save_value",
                self.save_addr_checkbox.isChecked()
                )

        self.settings.beginGroup("error")
        self.settings.setValue(
                "absolute",
                self.abs_radiobutton.isChecked()
                )
        self.settings.setValue(
                "level",
                self.error_level_doublespinbox.value()
                )
        self.settings.setValue(
                "color_norm",
                self.color_norm_button.toolTip()
                )
        self.settings.setValue(
                "color_error",
                self.color_error_button.toolTip()
                )
        self.settings.endGroup()

        self.settings.beginGroup("export")
        for column in range(1, 12):
            self.settings.setValue(
                    "column{}".format(column),
                    getattr(self, "column{}_checkbox".format(column)).isChecked()
                    )
        self.settings.endGroup()

    @QtCore.pyqtSlot(bool)
    def on_abs_radiobutton_toggled(self, checked):
        """
        Change error type.

        """
        if checked:
            self.error_units_label.setText(u"Ом")
            self.column3_checkbox.setText(u"Погрешность, Ом")
        else:
            self.error_units_label.setText("%")
            self.column3_checkbox.setText(u"Погрешность, %")

    @QtCore.pyqtSlot()
    def on_color_norm_button_clicked(self):
        """
        Select color for normal value.

        """
        color_norm = QtGui.QColor(self.color_norm_button.toolTip())
        color_norm = QtGui.QColorDialog.getColor(initial=color_norm)
        if color_norm.isValid():
            self.color_norm_button.setToolTip(color_norm.name())
            self.color_norm_button.setStyleSheet("QPushButton {{ background-color: {}}}".format(color_norm.name()))

    @QtCore.pyqtSlot()
    def on_color_error_button_clicked(self):
        """
        Select color for error value.

        """
        color_error = QtGui.QColor(self.color_error_button.toolTip())
        color_error = QtGui.QColorDialog.getColor(initial=color_error)
        if color_error.isValid():
            self.color_error_button.setToolTip(color_error.name())
            self.color_error_button.setStyleSheet("QPushButton {{ background-color: {}}}".format(color_error.name()))


class DiagnosticsDialog(QtGui.QDialog):
    """
    Dialog for SDKT-device diagnostics.

    """

    def __init__(self, parent=None):
        """
        Initializing of the diagnostics dialog.

        """
        QtGui.QDialog.__init__(self, parent)
        uic.loadUi('gui/diagnostics_dialog.ui', self)
        self.command_is_set = False

    def send_cmd_to_device(self, cmd, addr=0):
        """
        Send comand ot SDKT device.
            Supported comands:
            1 - reset;
            2 - set addres;
            3 - measure frequency;
            4 - set level 0 (0 V);
            5 - set level 1 (6 V);
            6 - set level 2 (12 V).

        """

        def wait():
            """
            Wait untill the command is executed.

            """
            for i in range(10):
                time.sleep(0.1)
                if sdkt_device.getControlMsg(1) == 0:
                    return
            else:
                QtGui.QMessageBox.critical(
                        self,
                        u"SDKT device",
                        u"Устройство не отвечает!\n" \
                        u"Превышено время ожидания ответа."
                        )
                sdkt_device.close()
                return

        try:
            sdkt_device = USBDeviceCustom()
            if sdkt_device.find():
                sdkt_device.open()
            else:
                QtGui.QMessageBox.critical(
                        self,
                        u"SDKT device",
                        u"Устройство не подключено или неисправно!"
                        )
                return
            if cmd == 1:
                sdkt_device.setControlMsg(1, 1)
            elif cmd == 2:
                sdkt_device.setControlMsg(2, addr)
                wait()
                sdkt_device.setControlMsg(1, 2)
            elif cmd == 4:
                sdkt_device.setControlMsg(1, 4)
            elif cmd == 5:
                sdkt_device.setControlMsg(1, 5)
            elif cmd == 6:
                sdkt_device.setControlMsg(1, 6)
            wait()
        except Exception, error:
            QtGui.QMessageBox.critical(
                    self,
                    u"SDKT device",
                    str(error)
                    )

    @QtCore.pyqtSlot(bool)
    def on_set_output_radiobutton_clicked(self, checked):
        """
        Set output ot specified level.

        """
        if checked:
            self.send_cmd_to_device(self.output_level_combobox.currentIndex() + 4)
            self.command_is_set = True

    @QtCore.pyqtSlot(bool)
    def on_set_addr_radiobutton_clicked(self, checked):
        """
        Set specified addres.

        """
        try:
            if checked:
                self.send_cmd_to_device(2, self.addr_spinbox.value())
                self.command_is_set = True
        except Exception, error:
            QtGui.QMessageBox.critical(
                    self,
                    u"Ошибка ввода",
                    str(error)
                    )

    @QtCore.pyqtSlot(bool)
    def on_reset_radiobutton_clicked(self, checked):
        """
        Reset SDKT device.

        """
        if checked:
            self.send_cmd_to_device(1, 1)
            self.command_is_set = False

    def closeEvent(self, event):
        """
        Reset SDKT device before closing.

        """
        if self.command_is_set:
            self.send_cmd_to_device(1)


class Measurement(QtCore.QThread):
    """
    Connects to the device and perform a measurement.

    """

    def __init__(self):
        """
        Initializing the thread of measurement.

        """
        QtCore.QThread.__init__(self)
        self.sensors = []

    def run(self):
        """
        Start mesuring.

        """

        def wait():
            """
            Wait until the command is executed.

            """
            for i in range(10):
                time.sleep(0.1)
                if sdkt_device.getControlMsg(1) == 0:
                    return
            else:
                self.emit(
                    QtCore.SIGNAL('error(QString, QString)'),
                    u'SDKT divice',
                    u'Устройство не отвечает!\n' \
                    u'Превышено время ожидания ответа.'
                    )
                sdkt_device.close()
                self.terminate()

        try:
            sdkt_device = USBDeviceCustom()
            if sdkt_device.find():
                sdkt_device.open()
            else:
                self.emit(
                    QtCore.SIGNAL('error(QString, QString)'),
                    u'SDKT device',
                    u'Устройство не подключено или неисправно!'
                    )
                return
            for addr in self.sensors:
                # Send sensor addr to device
                sdkt_device.setControlMsg(2, addr)
                wait()
                # Set addr
                sdkt_device.setControlMsg(1, 2)
                wait()
                # Measure the freaquency
                sdkt_device.setControlMsg(1, 3)
                wait()
                value = sdkt_device.getControlMsg(3)
                # Reset
                sdkt_device.setControlMsg(1, 1)
                if value in (0x0000, 0xFFFF):
                    value = 0
                self.emit(QtCore.SIGNAL('result(int, float)'), addr, value)
            sdkt_device.close()
            return
        except Exception, error:
            self.emit(
                QtCore.SIGNAL('error(QString, QString)'),
                u'SDKT device',
                str(error).decode("utf-8")
                )
            return


class CsvWriter:
    """
    A CSV writter for saving measured data.

    """

    def __init__(self, f):
        """
        Initialization of the whiter.

            f - file object for writing.

        """
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=csv.excel)
        self.stream = f
        self.encoder = codecs.getincrementalencoder("utf-8")()

    def writerow(self, row):
        """
        Write one row of the data to csv file.

        """
        self.writer.writerow([unicode(s).encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)


if __name__ == '__main__':
    """
    If this file was executed - start the program.

    """
    app = QtGui.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon("sdkt-tool.svg"))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

