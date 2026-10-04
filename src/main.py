"""Jira.app — lista as pessoas com acesso ao Jira em um combobox."""
import sys

from datetime import date, timedelta

from PySide6.QtCore import QDate, QObject, QThread, Qt, Signal
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QDateEdit,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

PERIODOS = ["Dia", "Semana", "Mês", "Ano"]


def intervalo(tipo: str, ref: date) -> tuple[date, date]:
    """[início, fim) do período que contém `ref` (semana: segunda a domingo)."""
    if tipo == "Dia":
        return ref, ref + timedelta(days=1)
    if tipo == "Semana":
        ini = ref - timedelta(days=ref.weekday())
        return ini, ini + timedelta(days=7)
    if tipo == "Mês":
        return ref.replace(day=1), date(ref.year + (ref.month == 12), ref.month % 12 + 1, 1)
    return date(ref.year, 1, 1), date(ref.year + 1, 1, 1)


def fmt_horas(seconds: int) -> str:
    h, m = divmod(round(seconds / 60), 60)
    return f"{h}h{m:02d}"

import config
from jira_client import JiraClient, JiraError


class UsersWorker(QObject):
    done = Signal(list)
    failed = Signal(str)

    def __init__(self, cfg: dict):
        super().__init__()
        self.cfg = cfg

    def run(self):
        try:
            client = JiraClient(self.cfg["url"], self.cfg["email"], self.cfg["token"])
            self.done.emit(client.get_users())
        except JiraError as e:
            self.failed.emit(str(e))
        except Exception as e:  # não deixar a thread morrer em silêncio
            self.failed.emit(f"Erro inesperado: {e}")


class HoursWorker(QObject):
    done = Signal(int, list)  # (id da requisição, resultado)
    failed = Signal(int, str)

    def __init__(self, cfg: dict, req_id: int, account_id: str, start: str, end: str):
        super().__init__()
        self.cfg, self.req_id = cfg, req_id
        self.account_id, self.start, self.end = account_id, start, end

    def run(self):
        try:
            client = JiraClient(self.cfg["url"], self.cfg["email"], self.cfg["token"])
            self.done.emit(self.req_id, client.get_worked_hours(self.account_id, self.start, self.end))
        except JiraError as e:
            self.failed.emit(self.req_id, str(e))
        except Exception as e:
            self.failed.emit(self.req_id, f"Erro inesperado: {e}")


class ConfigDialog(QDialog):
    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Conexão com o Jira")
        self.setMinimumWidth(420)
        self.url = QLineEdit(cfg.get("url", ""))
        self.url.setPlaceholderText("https://suaempresa.atlassian.net")
        self.email = QLineEdit(cfg.get("email", ""))
        self.token = QLineEdit(cfg.get("token", ""))
        self.token.setEchoMode(QLineEdit.Password)
        form = QFormLayout()
        form.addRow("URL do Jira", self.url)
        form.addRow("E-mail", self.email)
        form.addRow("API token", self.token)
        hint = QLabel(
            '<a href="https://id.atlassian.com/manage-profile/security/api-tokens">'
            "Criar API token</a>"
        )
        hint.setOpenExternalLinks(True)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(hint)
        lay.addWidget(buttons)

    def values(self) -> dict:
        return {"url": self.url.text().strip(), "email": self.email.text().strip(),
                "token": self.token.text().strip()}


class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jira")
        self.setMinimumSize(520, 520)
        self.cfg = config.load()
        self.thread = None
        self.hours_threads = []  # mantém as threads vivas até terminarem
        self.hours_req = 0
        self.total_prefixo = "Total: "

        self.combo = QComboBox()
        self.combo.setEditable(True)  # permite digitar para filtrar
        self.combo.setInsertPolicy(QComboBox.NoInsert)
        self.status = QLabel("")
        self.periodo = QComboBox()
        self.periodo.addItems(PERIODOS)
        self.periodo.setCurrentText("Mês")
        self.data = QDateEdit(QDate.currentDate())
        self.data.setCalendarPopup(True)
        self.data.setDisplayFormat("dd/MM/yyyy")
        self.total = QLabel("")
        self.total.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Issue", "Resumo", "Datas trabalhadas", "Horas"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.combo.currentIndexChanged.connect(self.load_hours)
        self.periodo.currentIndexChanged.connect(self.load_hours)
        self.data.dateChanged.connect(self.load_hours)
        self.reload_btn = QPushButton("Atualizar")
        self.reload_btn.clicked.connect(self.load_users)
        cfg_btn = QPushButton("Configurar conexão…")
        cfg_btn.clicked.connect(self.edit_config)

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Pessoas com acesso ao Jira:"))
        lay.addWidget(self.combo)
        lay.addWidget(self.status)
        periodo = QHBoxLayout()
        periodo.addWidget(QLabel("Período:"))
        periodo.addWidget(self.periodo)
        periodo.addWidget(QLabel("em"))
        periodo.addWidget(self.data)
        self.intervalo_lbl = QLabel("")
        periodo.addWidget(self.intervalo_lbl)
        periodo.addStretch()
        lay.addLayout(periodo)
        lay.addWidget(self.total)
        lay.addWidget(self.table)
        lay.addWidget(self.reload_btn)
        lay.addWidget(cfg_btn)

        if all(self.cfg.get(k) for k in ("url", "email", "token")):
            self.load_users()
        else:
            self.edit_config()

    def edit_config(self):
        dlg = ConfigDialog(self.cfg, self)
        if dlg.exec() == QDialog.Accepted:
            self.cfg = dlg.values()
            config.save(**self.cfg)
            self.load_users()

    def load_users(self):
        if self.thread and self.thread.isRunning():
            return
        self.combo.clear()
        self.reload_btn.setEnabled(False)
        self.status.setText("Carregando usuários…")
        self.thread = QThread(self)
        self.worker = UsersWorker(self.cfg)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.done.connect(self.on_users)
        self.worker.failed.connect(self.on_error)
        for sig in (self.worker.done, self.worker.failed):
            sig.connect(self.thread.quit)
        self.thread.start()

    def on_users(self, users: list):
        for u in users:
            self.combo.addItem(u.get("displayName", "?"), u.get("accountId"))
        self.status.setText(f"{len(users)} pessoas")
        self.reload_btn.setEnabled(True)

    def load_hours(self, *_):
        self.hours_req += 1  # invalida respostas de seleções anteriores
        self.table.setRowCount(0)
        account_id = self.combo.currentData()
        if not account_id:
            self.total.setText("")
            return
        tipo = self.periodo.currentText()
        ini, fim = intervalo(tipo, self.data.date().toPython())
        start, end = ini.isoformat(), fim.isoformat()
        self.intervalo_lbl.setText(f"({ini:%d/%m/%Y} a {fim - timedelta(days=1):%d/%m/%Y})")
        self.total_prefixo = f"Total ({tipo.lower()}): "
        self.total.setText("Calculando horas…")
        thread, worker = QThread(self), HoursWorker(self.cfg, self.hours_req, account_id, start, end)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.done.connect(self.on_hours)
        worker.failed.connect(self.on_hours_error)
        for sig in (worker.done, worker.failed):
            sig.connect(thread.quit)
        thread.finished.connect(lambda: self.hours_threads.remove((thread, worker)))
        self.hours_threads.append((thread, worker))
        thread.start()

    def on_hours(self, req_id: int, rows: list):
        if req_id != self.hours_req:
            return
        total = sum(r["seconds"] for r in rows)
        self.total.setText(f"{self.total_prefixo}{fmt_horas(total)}")
        self.table.setRowCount(len(rows) + 1)  # +1: linha de total consolidado
        for i, r in enumerate(rows):
            datas = ", ".join(f"{d[8:10]}/{d[5:7]}" for d in r["dates"])
            self.table.setItem(i, 0, QTableWidgetItem(r["key"]))
            self.table.setItem(i, 1, QTableWidgetItem(r["summary"]))
            self.table.setItem(i, 2, QTableWidgetItem(datas))
            self._set_horas(i, fmt_horas(r["seconds"]))
        fim = len(rows)
        todas = {d for r in rows for d in r["dates"]}
        for col, texto in enumerate(["TOTAL", "", f"{len(todas)} dia(s) trabalhado(s)"]):
            item = QTableWidgetItem(texto)
            item.setFont(self._negrito())
            self.table.setItem(fim, col, item)
        self._set_horas(fim, fmt_horas(total), negrito=True)

    def _negrito(self):
        f = self.table.font()
        f.setBold(True)
        return f

    def _set_horas(self, row: int, texto: str, negrito: bool = False):
        item = QTableWidgetItem(texto)
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        if negrito:
            item.setFont(self._negrito())
        self.table.setItem(row, 3, item)

    def on_hours_error(self, req_id: int, msg: str):
        if req_id != self.hours_req:
            return
        self.total.setText("Falha ao buscar horas.")
        QMessageBox.warning(self, "Erro", msg)

    def on_error(self, msg: str):
        self.status.setText("Falha ao carregar.")
        self.reload_btn.setEnabled(True)
        QMessageBox.warning(self, "Erro", msg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Window()
    win.show()
    sys.exit(app.exec())
