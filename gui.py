import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import services

def treeview_with_scroll(parent, columns, height=18):
    frame = ttk.Frame(parent)
    tree = ttk.Treeview(frame, columns=columns, show="headings", height=height)
    scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=max(90, 850 // len(columns)))
    tree.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    return frame, tree

def entries_from_labels(parent, labels, row=0):
    entries = {}
    for i, label in enumerate(labels):
        ttk.Label(parent, text=label).grid(row=row, column=i * 2, padx=3, sticky="e")
        entry = ttk.Entry(parent, width=15)
        entry.grid(row=row, column=i * 2 + 1, padx=3, pady=2)
        entries[label] = entry
    return entries

def fill_entries(entries, values):
    for entry, value in zip(entries.values(), values):
        entry.delete(0, "end")
        entry.insert(0, str(value) if value is not None else "")

def clear_entries(entries):
    for entry in entries.values():
        entry.delete(0, "end")

def get_selected_id(tree):
    selected = tree.selection()
    return tree.item(selected[0])["values"][0] if selected else None

def load_combobox(combobox, items, display_fn, value_fn):
    mapping = {}
    values = []
    for item in items:
        key = display_fn(item)
        values.append(key)
        mapping[key] = value_fn(item)
    if combobox is not None:
        combobox["values"] = values
        combobox.set("")
    return mapping

def ask_date(title):
    return simpledialog.askstring(title, "Дата (ГГГГ-ММ-ДД):")

def ask_int(title, prompt, default=1):
    return simpledialog.askinteger(title, prompt, initialvalue=default)

def ask_str(title, prompt):
    return simpledialog.askstring(title, prompt)

class CRUDFrame(ttk.Frame):
    def __init__(self, parent, database, table, id_column, columns, field_labels,
                 load_query, formatter, extra_widgets=None, on_select_callback=None,
                 before_insert=None, before_update=None):
        super().__init__(parent)
        self.database = database
        self.table = table
        self.id_column = id_column
        self.field_labels = field_labels
        self.load_query = load_query
        self.formatter = formatter
        self.on_select_callback = on_select_callback
        self._before_insert_hook = before_insert
        self._before_update_hook = before_update

        self.frame_tree, self.tree = treeview_with_scroll(self, columns)
        self.frame_tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        input_frame = ttk.Frame(self)
        input_frame.pack(fill="x", padx=5, pady=5)
        self.entries = entries_from_labels(input_frame, field_labels)

        if extra_widgets:
            extra_widgets(input_frame)

        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", padx=5, pady=5)
        ttk.Button(button_frame, text="Добавить", command=self._add).pack(side="left", padx=2)
        ttk.Button(button_frame, text="Изменить", command=self._update).pack(side="left", padx=2)
        ttk.Button(button_frame, text="Удалить", command=self._delete).pack(side="left", padx=2)
        ttk.Button(button_frame, text="Очистить", command=lambda: clear_entries(self.entries)).pack(side="left", padx=2)

    def load_data(self):
        self.tree.delete(*self.tree.get_children())
        for row in self.load_query():
            self.tree.insert("", "end", values=self.formatter(row))

    def _on_select(self, event):
        sel = self.tree.selection()
        if sel:
            values = self.tree.item(sel[0])["values"]
            fill_entries(self.entries, values[1:])
            if self.on_select_callback:
                self.on_select_callback(values)

    def _get_data(self):
        return {label: entry.get() for label, entry in self.entries.items() if entry.get()}

    def _add(self):
        data = self._get_data()
        if not data:
            return
        try:
            if self._before_insert_hook:
                self._before_insert_hook(data)
            services.insert(self.database, self.table, **data)
            self.load_data()
            clear_entries(self.entries)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def _update(self):
        rid = get_selected_id(self.tree)
        if not rid:
            return
        data = self._get_data()
        if not data:
            return
        try:
            if self._before_update_hook:
                self._before_update_hook(data)
            services.update(self.database, self.table, self.id_column, rid, **data)
            self.load_data()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def _delete(self):
        rid = get_selected_id(self.tree)
        if rid and messagebox.askyesno("Подтверждение", "Удалить запись?"):
            try:
                services.delete(self.database, self.table, self.id_column, rid)
                self.load_data()
                clear_entries(self.entries)
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

class App(tk.Tk):
    def __init__(self, database):
        super().__init__()
        self.database = database
        self.title("Ветеринарная клиника")
        self.geometry("950x650")

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        self.nb.add(DirectoriesTab(self.nb, database), text="Справочники")
        self.nb.add(EmployeesTab(self.nb, database), text="Сотрудники")
        self.nb.add(UsersTab(self.nb, database), text="Пользователи")
        self.nb.add(ClientsTab(self.nb, database), text="Клиенты")
        self.nb.add(PetsTab(self.nb, database), text="Питомцы")
        self.nb.add(AppointmentsTab(self.nb, database), text="Приемы")
        self.nb.add(HospitalizationsTab(self.nb, database), text="Госпитализации")

        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _on_tab_changed(self, event):
        current_tab = self.nb.nametowidget(self.nb.select())
        if hasattr(current_tab, "load_data"):
            current_tab.load_data()
        if isinstance(current_tab, PetsTab):
            current_tab._load_types()
            current_tab._load_breeds()
        elif isinstance(current_tab, EmployeesTab):
            current_tab._load_positions()
        elif isinstance(current_tab, AppointmentDialog):
            current_tab._load_clients()
            current_tab._load_pets()
            current_tab._load_doctors()
        elif isinstance(current_tab, HospitalizationDialog):
            current_tab._load_pets()
            current_tab._load_doctors()
            current_tab._load_wards()

class DirectoriesTab(ttk.Frame):
    def __init__(self, parent, database):
        super().__init__(parent)
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        configs = [
            ("Типы", "Pet_types", "type_id", ["name"], ["Название"]),
            ("Породы", "Breeds", "breed_id", ["pet_type_id", "name"], ["ID типа", "Название"]),
            ("Услуги", "Services", "service_id", ["name", "price"], ["Название", "Цена"]),
            ("Поставщики", "Suppliers", "supplier_id", ["company_name", "phone"], ["Компания", "Телефон"]),
            ("Товары", "Items", "item_id", ["supplier_id", "name", "price", "unit", "stock"], 
             ["ID поставщика", "Название", "Цена", "Ед. изм.", "Остаток"]),
            ("Должности", "Positions", "position_id", ["name"], ["Название"]),
        ]
        for title, table, id_col, field_keys, field_labels in configs:
            frame = self._make_directory_frame(nb, database, table, id_col, field_keys, field_labels)
            nb.add(frame, text=title)

        nb.add(WardFrame(nb, database), text="Палаты")

    def _make_directory_frame(self, parent, database, table, id_col, field_keys, field_labels):
        display_cols = ["ID"] + field_labels

        def load_query(t=table):
            return services.get_all(database, t)

        def formatter(row):
            return [row.get(id_col, "")] + [row.get(k, "") for k in field_keys]

        frame = CRUDFrame(
            parent, database, table, id_col, display_cols, field_labels,
            load_query=load_query,
            formatter=formatter,
            before_insert=lambda data: self._rename_keys(data, field_labels, field_keys),
            before_update=lambda data: self._rename_keys(data, field_labels, field_keys)
        )
        frame.load_data()
        return frame

    def _rename_keys(self, data, labels, keys):
        mapping = dict(zip(labels, keys))
        for label, key in mapping.items():
            if label in data:
                data[key] = data.pop(label)

class EmployeesTab(CRUDFrame):
    def __init__(self, parent, database):
        self._db = database
        self.position_map = {}
        self.position_combo = None

        def extra(frame):
            ttk.Label(frame, text="Должность").grid(row=1, column=0, padx=3, sticky="e")
            self.position_combo = ttk.Combobox(frame, width=14, state="readonly")
            self.position_combo.grid(row=1, column=1, padx=3, pady=2)
            self._load_positions()

        super().__init__(
            parent, database, "Employees", "employee_id",
            ["ID", "Фамилия", "Имя", "Отчество", "Должность", "Телефон", "Email"],
            ["Фамилия", "Имя", "Отчество", "Телефон", "Email"],
            load_query=lambda: services.get_employees(database),
            formatter=lambda e: [e["employee_id"], e["surname"], e["name"], e["third_name"], e["position"], e["phone"], e["email"]],
            extra_widgets=extra,
            on_select_callback=lambda v: self.position_combo.set(v[4] if v[4] else ""),
            before_insert=self._prepare_data,
            before_update=self._prepare_data
        )
        self.load_data()

    def _load_positions(self):
        positions = services.get_all(self._db, "Positions")
        self.position_map = load_combobox(self.position_combo, positions, lambda p: p["name"], lambda p: p["position_id"])

    def _prepare_data(self, data):
        data["position_id"] = self.position_map.get(self.position_combo.get())
        data["surname"] = data.pop("Фамилия", data.get("surname", ""))
        data["name"] = data.pop("Имя", data.get("name", ""))
        data["third_name"] = data.pop("Отчество", data.get("third_name", ""))
        data["phone"] = data.pop("Телефон", data.get("phone", ""))
        data["email"] = data.pop("Email", data.get("email", ""))

class ClientsTab(CRUDFrame):
    def __init__(self, parent, database):
        super().__init__(
            parent, database, "Clients", "client_id",
            ["ID", "Фамилия", "Имя", "Отчество", "Телефон", "Email"],
            ["Фамилия", "Имя", "Отчество", "Телефон", "Email"],
            load_query=lambda: services.get_clients(database),
            formatter=lambda c: [c["client_id"], c["surname"], c["name"], c["third_name"], c["phone"], c["email"]],
            before_insert=self._prepare_data,
            before_update=self._prepare_data
        )
        ttk.Button(self, text="Питомцы клиента", command=self._open_pets).pack(pady=5)
        self.load_data()

    def _prepare_data(self, data):
        data["surname"] = data.pop("Фамилия", data.get("surname", ""))
        data["name"] = data.pop("Имя", data.get("name", ""))
        data["third_name"] = data.pop("Отчество", data.get("third_name", ""))
        data["phone"] = data.pop("Телефон", data.get("phone", ""))
        data["email"] = data.pop("Email", data.get("email", ""))

    def _open_pets(self):
        cid = get_selected_id(self.tree)
        if cid:
            ClientPetsWindow(self, self.database, cid)
        else:
            messagebox.showwarning("Внимание", "Выберите клиента")

class ClientPetsWindow(tk.Toplevel):
    def __init__(self, parent, database, client_id):
        super().__init__(parent)
        self.database, self.client_id = database, client_id
        self.title("Питомцы клиента")
        self.geometry("500x450")

        self.frame_tree, self.tree = treeview_with_scroll(self, ["ID связи", "Кличка", "Порода", "Тип", "Владелец"])
        self.frame_tree.pack(fill="both", expand=True, padx=5, pady=5)

        bf = ttk.Frame(self)
        bf.pack(fill="x", padx=5, pady=5)
        ttk.Button(bf, text="Привязать", command=self._link).pack(side="left", padx=2)
        ttk.Button(bf, text="Отвязать", command=self._unlink).pack(side="left", padx=2)
        self._load()

    def _load(self):
        self.tree.delete(*self.tree.get_children())
        for pet in services.get_pets_by_client(self.database, self.client_id):
            self.tree.insert("", "end", values=[
                pet["client_pet_id"],
                pet["name"],
                pet["breed"] if "breed" in pet else "",
                pet["type"] if "type" in pet else "",
                "Да" if pet.get("is_owner") else "Нет"
            ])

    def _link(self):
        all_pets = services.get_pets(self.database)
        if not all_pets:
            messagebox.showinfo("Информация", "Нет питомцев в базе")
            return

        linked = services.get_pets_by_client(self.database, self.client_id)
        linked_ids = {p["pet_id"] for p in linked}

        available = [p for p in all_pets if p["pet_id"] not in linked_ids]
        if not available:
            messagebox.showinfo("Информация", "Все питомцы уже привязаны")
            return

        dialog = tk.Toplevel(self)
        dialog.title("Привязать питомца")
        dialog.geometry("450x200")
        dialog.resizable(False, False)

        ttk.Label(dialog, text="Выберите питомца:").pack(pady=(15, 5))
        
        pet_combo = ttk.Combobox(
            dialog,
            values=[f'{p["pet_id"]} — {p["name"]} ({p.get("breed", "")})' for p in available],
            width=45,
            state="readonly"
        )
        pet_combo.pack(padx=10, pady=5)
        if available:
            pet_combo.set(f'{available[0]["pet_id"]} — {available[0]["name"]} ({available[0].get("breed", "")})')

        result = {"pet_id": None}

        def save():
            selected = pet_combo.get()
            if selected:
                pet_id = int(selected.split(" — ")[0])
                result["pet_id"] = pet_id
            dialog.destroy()

        ttk.Button(dialog, text="Привязать", command=save).pack(pady=15)
        dialog.wait_window()

        if result["pet_id"]:
            try:
                services.link_pet_to_client(self.database, self.client_id, result["pet_id"])
                self._load()
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

    def _unlink(self):
        cpid = get_selected_id(self.tree)
        if cpid and messagebox.askyesno("?", "Отвязать питомца?"):
            try:
                services.unlink_pet_from_client(self.database, cpid)
                self._load()
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

class PetsTab(CRUDFrame):
    def __init__(self, parent, database):
        self._db = database
        self.breed_map = {}
        self.type_map = {}
        self.breed_combo = None
        self.gender_combo = None

        def extra(frame):
            ttk.Label(frame, text="Порода").grid(row=0, column=6, padx=3, sticky="e")
            self.breed_combo = ttk.Combobox(frame, width=14, state="readonly")
            self.breed_combo.grid(row=0, column=7, padx=3)
            ttk.Label(frame, text="Пол").grid(row=1, column=6, padx=3, sticky="e")
            self.gender_combo = ttk.Combobox(frame, values=["М", "Ж"], width=14, state="readonly")
            self.gender_combo.grid(row=1, column=7, padx=3)

        super().__init__(
            parent, database, "Pets", "pet_id",
            ["ID", "Кличка", "Порода", "Тип", "Пол", "Окрас", "Дата рождения"],
            ["Кличка", "Окрас", "Дата рождения"],
            load_query=self._load_pets,
            formatter=lambda p: [p["pet_id"], p["name"], p["breed"], p["type"], p["gender"], p["color"] or "", p["birth_date"] or ""],
            extra_widgets=extra,
            on_select_callback=lambda v: [self.breed_combo.set(v[2]), self.gender_combo.set(v[4])],
            before_insert=self._prepare_data,
            before_update=self._prepare_data
        )

        self._load_breeds()

        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(filter_frame, text="Тип:").pack(side="left")
        self.type_filter = ttk.Combobox(filter_frame, width=15, state="readonly")
        self.type_filter.pack(side="left", padx=5)
        self.type_filter.bind("<<ComboboxSelected>>", lambda e: self.load_data())
        ttk.Button(filter_frame, text="Сброс", command=self._reset_filter).pack(side="left", padx=5)
        self._load_types()
        self.load_data()

    def _load_types(self):
        types = services.get_all(self._db, "Pet_types")
        self.type_filter["values"] = ["Все"] + [t["name"] for t in types]
        self.type_filter.set("Все")
        self.type_map = {t["name"]: t["type_id"] for t in types}

    def _load_breeds(self):
        self.breed_map = load_combobox(self.breed_combo, services.get_all(self._db, "Breeds"), lambda b: b["name"], lambda b: b["breed_id"])

    def _reset_filter(self):
        self.type_filter.set("Все")
        self.load_data()

    def _load_pets(self):
        tid = self.type_map.get(self.type_filter.get()) if self.type_filter.get() != "Все" else None
        return services.get_pets(self._db, tid)

    def _prepare_data(self, data):
        data["breed_id"] = self.breed_map.get(self.breed_combo.get())
        data["gender"] = self.gender_combo.get()
        data["birth_date"] = data.pop("Дата рождения", None) or None
        data["color"] = data.pop("Окрас", None) or None
        data["name"] = data.pop("Кличка", data.get("name", ""))

class UsersTab(ttk.Frame):
    def __init__(self, parent, database):
        super().__init__(parent)
        self.database = database

        self.frame_tree, self.tree = treeview_with_scroll(self, ["ID", "Логин", "Роль", "Сотрудник/Клиент"])
        self.frame_tree.pack(fill="both", expand=True, padx=5, pady=5)

        frm = ttk.Frame(self)
        frm.pack(fill="x", padx=5, pady=5)

        self.bind_type = tk.StringVar(value="employee")
        ttk.Radiobutton(frm, text="Сотрудник", variable=self.bind_type, value="employee", command=self._toggle).grid(row=0, column=0)
        ttk.Radiobutton(frm, text="Клиент", variable=self.bind_type, value="client", command=self._toggle).grid(row=0, column=1)
        self.bind_combo = ttk.Combobox(frm, width=30, state="readonly")
        self.bind_combo.grid(row=1, column=0, columnspan=2, pady=3)

        ttk.Label(frm, text="Логин").grid(row=2, column=0, sticky="e")
        self.login_entry = ttk.Entry(frm, width=25)
        self.login_entry.grid(row=2, column=1, padx=5)

        ttk.Label(frm, text="Пароль").grid(row=3, column=0, sticky="e")
        self.pw_entry = ttk.Entry(frm, width=25, show="*")
        self.pw_entry.grid(row=3, column=1, padx=5)

        ttk.Label(frm, text="Роль").grid(row=4, column=0, sticky="e")
        self.role_combo = ttk.Combobox(frm, values=["admin", "doctor", "client"], width=22, state="readonly")
        self.role_combo.grid(row=4, column=1, padx=5)

        bf = ttk.Frame(self)
        bf.pack(fill="x", padx=5, pady=5)
        ttk.Button(bf, text="Создать", command=self._create).pack(side="left", padx=2)
        ttk.Button(bf, text="Удалить", command=self._delete).pack(side="left", padx=2)

        self.emp_map, self.cli_map = {}, {}
        self._toggle()
        self.load_data()

    def _toggle(self):
        if self.bind_type.get() == "employee":
            self.emp_map = load_combobox(self.bind_combo, services.get_employees(self.database),
                                         lambda e: '{e["surname"]} {e["name"]}', lambda e: e["employee_id"])
        else:
            self.cli_map = load_combobox(self.bind_combo, services.get_clients(self.database),
                                         lambda c: f'{c["surname"]} {c["name"]}', lambda c: c["client_id"])

    def load_data(self):
        self.tree.delete(*self.tree.get_children())
        for u in services.get_users(self.database):
            self.tree.insert("", "end", values=[u["user_id"], u["username"], u["role"], u["employee_name"] or u["client_name"] or ""])

    def _create(self):
        login = self.login_entry.get().strip()
        pw = self.pw_entry.get().strip()
        role = self.role_combo.get()
        if not login or not pw or not role:
            return messagebox.showwarning("Внимание", "Заполните все поля")
        eid = self.emp_map.get(self.bind_combo.get()) if self.bind_type.get() == "employee" else None
        cid = self.cli_map.get(self.bind_combo.get()) if self.bind_type.get() == "client" else None
        try:
            services.create_user(self.database, eid, cid, login, pw, role)
            self.load_data()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def _delete(self):
        uid = get_selected_id(self.tree)
        if uid and messagebox.askyesno("?", "Удалить?"):
            services.delete(self.database, "Users", "user_id", uid)
            self.load_data()

class AppointmentsTab(ttk.Frame):
    def __init__(self, parent, database):
        super().__init__(parent)
        self.database = database

        ff = ttk.Frame(self)
        ff.pack(fill="x", padx=5, pady=5)
        ttk.Label(ff, text="Дата:").pack(side="left")
        self.filter_date = ttk.Entry(ff, width=12)
        self.filter_date.pack(side="left", padx=5)
        ttk.Label(ff, text="Статус:").pack(side="left")
        self.filter_status = ttk.Combobox(ff, values=["", "запланирован", "завершён", "отменён"], width=12, state="readonly")
        self.filter_status.pack(side="left", padx=5)
        ttk.Button(ff, text="Фильтр", command=self.load_data).pack(side="left", padx=5)
        ttk.Button(ff, text="Сброс", command=self._reset).pack(side="left")

        self.frame_tree, self.tree = treeview_with_scroll(self, ["ID", "Клиент", "Питомец", "Врач", "Дата", "Статус"])
        self.frame_tree.pack(fill="both", expand=True, padx=5, pady=5)

        bf = ttk.Frame(self)
        bf.pack(fill="x", padx=5, pady=5)
        for text, cmd in [("Создать", self._create), ("Статус", self._status), ("Услуги", self._services),
                          ("Препараты", self._items), ("Медзапись", self._med), ("Удалить", self._delete)]:
            ttk.Button(bf, text=text, command=cmd).pack(side="left", padx=2)
        self.load_data()

    def load_data(self):
        self.tree.delete(*self.tree.get_children())
        fd = self.filter_date.get().strip() or None
        fs = self.filter_status.get() or None
        for a in services.get_appointments(self.database, fd, fs):
            self.tree.insert("", "end", values=[a["appointment_id"], a["client"], a["pet"], a["doctor"], a["appointment_date"], a["status"]])

    def _reset(self):
        self.filter_date.delete(0, "end")
        self.filter_status.set("")
        self.load_data()

    def _create(self):
        dlg = AppointmentDialog(self, self.database)
        if dlg.result:
            services.create_appointment(self.database, dlg.result["pet_id"], dlg.result["doctor_id"], dlg.result["appointment_date"])
            self.load_data()

    def _status(self):
        aid = get_selected_id(self.tree)
        if not aid:
            return

        dialog = tk.Toplevel(self)
        dialog.title("Изменить статус")
        dialog.geometry("300x120")
        dialog.resizable(False, False)
        
        ttk.Label(dialog, text="Новый статус:").pack(pady=(15, 5))
        status_combo = ttk.Combobox(
            dialog, 
            values=["запланирован", "завершён", "отменён"],
            width=25,
            state="readonly"
        )
        status_combo.pack(padx=10, pady=5)
        status_combo.set("завершён")
        
        result = {"status": None}
        
        def save():
            result["status"] = status_combo.get()
            dialog.destroy()
        
        ttk.Button(dialog, text="ОК", command=save).pack(pady=10)
        dialog.wait_window()
        
        if result["status"]:
            services.update_appointment_status(self.database, aid, result["status"])
            self.load_data()

    def _services(self):
        aid = get_selected_id(self.tree)
        if aid:
            SubItemsWindow(self, self.database, aid, "services")

    def _items(self):
        aid = get_selected_id(self.tree)
        if aid:
            SubItemsWindow(self, self.database, aid, "items")

    def _med(self):
        aid = get_selected_id(self.tree)
        if aid:
            MedicalRecordWindow(self, self.database, appointment_id=aid)

    def _delete(self):
        aid = get_selected_id(self.tree)
        if aid and messagebox.askyesno("?", "Удалить прием?"):
            services.delete(self.database, "Appointments", "appointment_id", aid)
            self.load_data()

class HospitalizationsTab(ttk.Frame):
    def __init__(self, parent, database):
        super().__init__(parent)
        self.database = database

        self.frame_tree, self.tree = treeview_with_scroll(self, ["ID", "Питомец", "Палата", "Врач", "Дата пост.", "Дата вып.", "Статус"])
        self.frame_tree.pack(fill="both", expand=True, padx=5, pady=5)

        bf = ttk.Frame(self)
        bf.pack(fill="x", padx=5, pady=5)
        for text, cmd in [("Госпитализировать", self._create), ("Выписать", self._discharge),
                          ("Отменить", self._cancel), ("Медзапись", self._med)]:
            ttk.Button(bf, text=text, command=cmd).pack(side="left", padx=2)
        self.load_data()

    def load_data(self):
        self.tree.delete(*self.tree.get_children())
        for h in services.get_hospitalizations(self.database):
            self.tree.insert("", "end", values=[h["hospitalization_id"], h["pet"], h["room_number"], h["doctor"], h["admission_date"], h["discharge_date"] or "", h["status"]])

    def _create(self):
        dlg = HospitalizationDialog(self, self.database)
        if dlg.result:
            services.create_hospitalization(self.database, dlg.result["pet_id"], dlg.result["doctor_id"], dlg.result["ward_id"], dlg.result["admission_date"])
            self.load_data()

    def _discharge(self):
        hid = get_selected_id(self.tree)
        if hid:
            d = ask_date("Дата выписки")
            if d:
                services.discharge_hospitalization(self.database, hid, d)
                self.load_data()

    def _cancel(self):
        hid = get_selected_id(self.tree)
        if hid and messagebox.askyesno("?", "Отменить госпитализацию?"):
            services.cancel_hospitalization(self.database, hid)
            self.load_data()

    def _med(self):
        hid = get_selected_id(self.tree)
        if hid:
            MedicalRecordWindow(self, self.database, hospitalization_id=hid)

class AppointmentDialog(tk.Toplevel):
    def __init__(self, parent, database):
        super().__init__(parent)
        self.database = database
        self.result = None
        self.title("Создать прием")
        self.geometry("450x280")

        self.client_combo = None
        self.pet_combo = None
        self.doctor_combo = None
        self.client_map = {}
        self.pet_map = {}
        self.doctor_map = {}

        ttk.Label(self, text="Клиент:").pack(pady=(10, 0))
        self.client_combo = ttk.Combobox(self, width=40, state="readonly")
        self.client_combo.pack(padx=10, pady=2)
        self.client_combo.bind("<<ComboboxSelected>>", self._load_pets)

        ttk.Label(self, text="Питомец:").pack()
        self.pet_combo = ttk.Combobox(self, width=40, state="readonly")
        self.pet_combo.pack(padx=10, pady=2)

        ttk.Label(self, text="Врач:").pack()
        self.doctor_combo = ttk.Combobox(self, width=40, state="readonly")
        self.doctor_combo.pack(padx=10, pady=2)

        ttk.Label(self, text="Дата и время (ГГГГ-ММ-ДД ЧЧ:ММ):").pack()
        self.date_entry = ttk.Entry(self, width=25)
        self.date_entry.pack(padx=10, pady=2)

        ttk.Button(self, text="Сохранить", command=self._save).pack(pady=15)

        self._load_clients()
        self._load_doctors()
        self.wait_window()

    def _load_clients(self):
        clients = services.get_clients(self.database)
        self.client_map = load_combobox(self.client_combo, clients, lambda c: f'{c["surname"]} {c["name"]}', lambda c: c["client_id"])

    def _load_pets(self, event):
        cid = self.client_map.get(self.client_combo.get())
        if cid:
            pets = services.get_pets_by_client(self.database, cid)
            self.pet_map = load_combobox(self.pet_combo, pets, lambda p: f'{p["name"]} ({p["breed"]})', lambda p: p["pet_id"])

    def _load_doctors(self):
        doctors = services.get_employees(self.database)
        self.doctor_map = load_combobox(self.doctor_combo, doctors, lambda e: f'{e["surname"]} {e["name"]}', lambda e: e["employee_id"])

    def _save(self):
        pid = self.pet_map.get(self.pet_combo.get())
        did = self.doctor_map.get(self.doctor_combo.get())
        date = self.date_entry.get().strip()
        if not pid or not did or not date:
            messagebox.showwarning("Внимание", "Заполните все поля")
            return
        self.result = {"pet_id": pid, "doctor_id": did, "appointment_date": date}
        self.destroy()

class HospitalizationDialog(tk.Toplevel):
    def __init__(self, parent, database):
        super().__init__(parent)
        self.database = database
        self.result = None
        self.title("Госпитализировать")
        self.geometry("450x280")

        self.pet_combo = None
        self.doctor_combo = None
        self.ward_combo = None
        self.pet_map = {}
        self.doctor_map = {}
        self.ward_map = {}

        ttk.Label(self, text="Питомец:").pack(pady=(10, 0))
        self.pet_combo = ttk.Combobox(self, width=40, state="readonly")
        self.pet_combo.pack(padx=10, pady=2)

        ttk.Label(self, text="Врач:").pack()
        self.doctor_combo = ttk.Combobox(self, width=40, state="readonly")
        self.doctor_combo.pack(padx=10, pady=2)

        ttk.Label(self, text="Палата:").pack()
        self.ward_combo = ttk.Combobox(self, width=40, state="readonly")
        self.ward_combo.pack(padx=10, pady=2)

        ttk.Label(self, text="Дата поступления (ГГГГ-ММ-ДД):").pack()
        self.date_entry = ttk.Entry(self, width=25)
        self.date_entry.pack(padx=10, pady=2)

        ttk.Button(self, text="Сохранить", command=self._save).pack(pady=15)

        self._load_pets()
        self._load_doctors()
        self._load_wards()
        self.wait_window()

    def _load_pets(self):
        pets = services.get_pets(self.database)
        self.pet_map = load_combobox(self.pet_combo, pets, lambda p: f'{p["pet_id"]} — {p["name"]} ({p["breed"]})', lambda p: p["pet_id"])

    def _load_doctors(self):
        doctors = services.get_employees(self.database)
        self.doctor_map = load_combobox(self.doctor_combo, doctors, lambda e: f'{e["surname"]} {e["name"]}', lambda e: e["employee_id"])

    def _load_wards(self):
        wards = services.get_all(self.database, "Ward_rooms")
        available = [w for w in wards if w["is_available"]]
        self.ward_map = load_combobox(self.ward_combo, available, lambda w: f'№{w["room_number"]}', lambda w: w["room_id"])

    def _save(self):
        pid = self.pet_map.get(self.pet_combo.get())
        did = self.doctor_map.get(self.doctor_combo.get())
        wid = self.ward_map.get(self.ward_combo.get())
        date = self.date_entry.get().strip()
        if not pid or not did or not wid or not date:
            messagebox.showwarning("Внимание", "Заполните все поля")
            return
        self.result = {"pet_id": pid, "doctor_id": did, "ward_id": wid, "admission_date": date}
        self.destroy()

class SubItemsWindow(tk.Toplevel):
    def __init__(self, parent, database, parent_id, mode):
        super().__init__(parent)
        self.database, self.parent_id, self.mode = database, parent_id, mode
        self.title("Услуги приема" if mode == "services" else "Препараты приема")
        self.geometry("550x450")

        cols = ["ID", "Название", "Кол-во"] + (["Дозировка"] if mode == "items" else []) + ["Цена"]
        self.frame_tree, self.tree = treeview_with_scroll(self, cols)
        self.frame_tree.pack(fill="both", expand=True, padx=5, pady=5)

        bf = ttk.Frame(self)
        bf.pack(fill="x", padx=5, pady=5)
        ttk.Button(bf, text="Добавить", command=self._add).pack(side="left", padx=2)
        ttk.Button(bf, text="Удалить", command=self._delete).pack(side="left", padx=2)
        self._load()

    @property
    def _table(self):
        return "Appointment_services" if self.mode == "services" else "Appointment_items"

    @property
    def _id_col(self):
        return "appointment_service_id" if self.mode == "services" else "appointment_item_id"

    @property
    def _source_table(self):
        return "Services" if self.mode == "services" else "Items"

    def _load(self):
        self.tree.delete(*self.tree.get_children())
        if self.mode == "services":
            for s in services.get_appointment_services(self.database, self.parent_id):
                self.tree.insert("", "end", values=[s["appointment_service_id"], s["service_name"], s["quantity"], s["price"]])
        else:
            for i in services.get_appointment_items(self.database, self.parent_id):
                self.tree.insert("", "end", values=[i["appointment_item_id"], i["item_name"], i["quantity"], i["dosage"] or "", i["price"]])

    def _add(self):
        items = services.get_all(self.database, self._source_table)
        if not items:
            messagebox.showinfo("Информация", "Нет данных в справочнике")
            return

        dialog = tk.Toplevel(self)
        dialog.title("Добавить")
        dialog.geometry("400x250")
        dialog.resizable(False, False)

        ttk.Label(dialog, text="Выберите:").pack(pady=(10, 0))
        combo = ttk.Combobox(dialog, values=[item["name"] for item in items], width=40, state="readonly")
        combo.pack(padx=10, pady=5)
        if items:
            combo.set(items[0]["name"])

        ttk.Label(dialog, text="Количество:").pack()
        qty_entry = ttk.Entry(dialog, width=20)
        qty_entry.pack(pady=2)
        qty_entry.insert(0, "1")

        dosage_entry = None
        if self.mode == "items":
            ttk.Label(dialog, text="Дозировка:").pack()
            dosage_entry = ttk.Entry(dialog, width=30)
            dosage_entry.pack(pady=2)

        result = {"name": None, "qty": None, "dosage": None}

        def save():
            name = combo.get()
            qty_str = qty_entry.get().strip()
            if not name or not qty_str:
                return
            try:
                qty = int(qty_str)
                if qty <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Ошибка", "Количество должно быть положительным целым числом")
                return
            result["name"] = name
            result["qty"] = qty
            if dosage_entry:
                result["dosage"] = dosage_entry.get().strip() or None
            dialog.destroy()

        ttk.Button(dialog, text="Добавить", command=save).pack(pady=10)
        dialog.wait_window()

        if result["name"] and result["qty"]:
            # Ищем выбранный элемент
            selected = next((item for item in items if item["name"] == result["name"]), None)
            if selected:
                try:
                    if self.mode == "services":
                        services.add_service_to_appointment(
                            self.database, self.parent_id, selected["service_id"], result["qty"], selected["price"]
                        )
                    else:
                        services.add_item_to_appointment(
                            self.database, self.parent_id, selected["item_id"], result["qty"], result["dosage"], selected["price"]
                        )
                        services.update_stock(self.database, selected["item_id"], -result["qty"])
                    self._load()
                except Exception as e:
                    messagebox.showerror("Ошибка", str(e))

    def _delete(self):
        sid = get_selected_id(self.tree)
        if not sid:
            return
        if not messagebox.askyesno("?", "Удалить?"):
            return
        if self.mode == "items":
            vals = self.tree.item(self.tree.selection()[0])["values"]
            real_id = services.get_item_id_by_name(self.database, vals[1])
            if real_id:
                services.update_stock(self.database, real_id, vals[2])
        services.delete(self.database, self._table, self._id_col, sid)
        self._load()

class MedicalRecordWindow(tk.Toplevel):
    def __init__(self, parent, database, appointment_id=None, hospitalization_id=None):
        super().__init__(parent)
        self.database, self.app_id, self.hosp_id = database, appointment_id, hospitalization_id
        self.title("Медицинская запись")
        self.geometry("450x400")

        self.existing = services.get_medical_record(database, appointment_id, hospitalization_id)

        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(frm, text="Причина обращения:").pack(anchor="w")
        self.reason = tk.Text(frm, height=2, width=50)
        self.reason.pack(pady=(0, 5))

        ttk.Label(frm, text="Диагноз:").pack(anchor="w")
        self.diag = tk.Text(frm, height=2, width=50)
        self.diag.pack(pady=(0, 5))

        ttk.Label(frm, text="Температура:").pack(anchor="w")
        self.temp = ttk.Entry(frm, width=20)
        self.temp.pack(pady=(0, 5))

        ttk.Label(frm, text="Вес:").pack(anchor="w")
        self.weight = ttk.Entry(frm, width=20)
        self.weight.pack(pady=(0, 5))

        ttk.Label(frm, text="Рекомендации:").pack(anchor="w")
        self.recs = tk.Text(frm, height=2, width=50)
        self.recs.pack(pady=(0, 10))

        if self.existing:
            self.reason.insert("1.0", self.existing.get("reason", "") or "")
            self.diag.insert("1.0", self.existing.get("diagnosis", "") or "")
            self.temp.insert(0, str(self.existing.get("temperature", "")))
            self.weight.insert(0, str(self.existing.get("weight", "")))
            self.recs.insert("1.0", self.existing.get("recommendations", "") or "")

        ttk.Button(frm, text="Сохранить", command=self._save).pack(pady=10)

    def _save(self):
        temp_val = self.temp.get().strip()
        weight_val = self.weight.get().strip()
        try:
            t = float(temp_val) if temp_val else None
            w = float(weight_val) if weight_val else None
        except ValueError:
            return messagebox.showwarning("Ошибка", "Некорректное числовое значение")
        services.save_medical_record(
            self.database,
            self.existing["record_id"] if self.existing else None,
            self.app_id, self.hosp_id,
            self.reason.get("1.0", "end-1c").strip() or None,
            self.diag.get("1.0", "end-1c").strip() or None,
            t, w,
            self.recs.get("1.0", "end-1c").strip() or None
        )
        self.destroy()

class WardFrame(ttk.Frame):
    def __init__(self, parent, database):
        super().__init__(parent)
        self.database = database
        self.table = "Ward_rooms"
        self.id_column = "room_id"

        cols = ["room_id", "Номер", "Цена/день", "Доступна"]
        self.frame_tree, self.tree = treeview_with_scroll(self, cols)
        self.frame_tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        frm = ttk.Frame(self)
        frm.pack(fill="x", padx=5, pady=5)

        ttk.Label(frm, text="Номер").grid(row=0, column=0, padx=3, sticky="e")
        self.room_entry = ttk.Entry(frm, width=15)
        self.room_entry.grid(row=0, column=1, padx=3)

        ttk.Label(frm, text="Цена/день").grid(row=0, column=2, padx=3, sticky="e")
        self.price_entry = ttk.Entry(frm, width=15)
        self.price_entry.grid(row=0, column=3, padx=3)

        ttk.Label(frm, text="Доступна").grid(row=0, column=4, padx=3, sticky="e")
        self.avail_combo = ttk.Combobox(frm, values=["Да", "Нет"], width=13, state="readonly")
        self.avail_combo.grid(row=0, column=5, padx=3)
        self.avail_combo.set("Да")

        bf = ttk.Frame(self)
        bf.pack(fill="x", padx=5, pady=5)
        ttk.Button(bf, text="Добавить", command=self._add).pack(side="left", padx=2)
        ttk.Button(bf, text="Изменить", command=self._upd).pack(side="left", padx=2)
        ttk.Button(bf, text="Удалить", command=self._del).pack(side="left", padx=2)
        ttk.Button(bf, text="Очистить", command=self._clear).pack(side="left", padx=2)

        self.load_data()

    def load_data(self):
        self.tree.delete(*self.tree.get_children())
        for row in services.get_all(self.database, self.table):
            self.tree.insert("", "end", values=[
                row["room_id"], row["room_number"], row["price_per_day"],
                "Да" if row["is_available"] else "Нет"
            ])

    def _on_select(self, event):
        sel = self.tree.selection()
        if sel:
            v = self.tree.item(sel[0])["values"]
            self.room_entry.delete(0, "end")
            self.room_entry.insert(0, str(v[1] or ""))
            self.price_entry.delete(0, "end")
            self.price_entry.insert(0, str(v[2] or ""))
            self.avail_combo.set(v[3])

    def _clear(self):
        self.room_entry.delete(0, "end")
        self.price_entry.delete(0, "end")
        self.avail_combo.set("Да")

    def _add(self):
        try:
            services.insert(self.database, self.table,
                            room_number=int(self.room_entry.get()),
                            price_per_day=float(self.price_entry.get()),
                            is_available=self.avail_combo.get() == "Да")
            self.load_data()
            self._clear()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def _upd(self):
        rid = get_selected_id(self.tree)
        if not rid:
            return
        try:
            services.update(self.database, self.table, self.id_column, rid,
                            room_number=int(self.room_entry.get()),
                            price_per_day=float(self.price_entry.get()),
                            is_available=self.avail_combo.get() == "Да")
            self.load_data()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def _del(self):
        rid = get_selected_id(self.tree)
        if rid and messagebox.askyesno("?", "Удалить?"):
            services.delete(self.database, self.table, self.id_column, rid)
            self.load_data()
            self._clear()