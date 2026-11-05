import os
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QGroupBox, QComboBox, QSizePolicy, QFrame
)
from PyQt5.QtCore import Qt, QTimer
from ruamel.yaml import YAML


def normalize_topic(s):
    s=(s or "").strip()
    return ("/"+s.lstrip("/")) if s else ""


class ProfileYamlEditor(QWidget):
    def __init__(self, mplanner_yaml_path, sensors_yaml_path, width=400, signal_bus=None):
        super().__init__()

        self.signal_bus = signal_bus
        self.mplanner_yaml_path = mplanner_yaml_path
        self.sensors_yaml_path = sensors_yaml_path
        self.setFixedWidth(width)

        self.profile_widgets = []
        self.planner_names = []
        self.hubs = {}

        self.load_mplanner()
        self.load_sensors()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        title = QLabel("Profiles")
        title.setStyleSheet("font-weight:bold; font-size:14px;")
        main_layout.addWidget(title)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        content = QWidget()
        self.profile_column = QVBoxLayout(content)
        self.profile_column.setAlignment(Qt.AlignTop)

        self.scroll.setWidget(content)
        main_layout.addWidget(self.scroll)

        btns = QHBoxLayout()
        add_btn = QPushButton("+ Add Profile")
        add_btn.clicked.connect(self.add_profile)
        save_btn = QPushButton("Save YAML")
        save_btn.clicked.connect(self.save_yaml)
        btns.addWidget(add_btn)
        btns.addWidget(save_btn)
        btns.addStretch()
        main_layout.addLayout(btns)

        # Maps GUI field labels -> the YAML/constructor key. These keys are
        # splatted directly into the optimizer constructor by ExoStack
        # (OptimizerClass(**hil_hyperparams)), so every key here MUST be a valid
        # argument of OPT_BAYESIAN / OPT_CMA_ES. The on-screen label may be a
        # friendly name (e.g. "Acquisition Function") while the saved key is the
        # optimizer's real argument name ("kind"). GP params are handled
        # separately (nested under "gp_params").
        self.HIL_LABEL_KEY_MAP = {
        "init_points": "init_points",
        "max_iters": "max_iters",
        "xi": "xi",
        "kappa": "kappa",
        "sigma": "sigma",
        "population_size": "population_size",
        "max_generations": "max_generations",
        "n_max_resampling": "n_max_resampling",
        "Acquisition Function": "kind",
        }


        # 🔹 LOAD EXISTING YAML OR CREATE EMPTY
        self.load_profiles_from_yaml()

    # ------------------------------------------------------------
    # LOAD YAMLs
    # ------------------------------------------------------------
    def load_mplanner(self):
        yaml = YAML()
        if os.path.exists(self.mplanner_yaml_path):
            with open(self.mplanner_yaml_path) as f:
                data = yaml.load(f) or {}
            self.planner_names = list(data.get("planners", {}).keys())

    def load_sensors(self):
        yaml = YAML()
        if os.path.exists(self.sensors_yaml_path):
            with open(self.sensors_yaml_path) as f:
                data = yaml.load(f) or {}
            self.hubs = data.get("hubs", {})

    # ------------------------------------------------------------
    # LOAD PROFILES YAML
    # ------------------------------------------------------------
    def load_profiles_from_yaml(self):
        path = os.path.expanduser("~/exo_stack_resources/config/profile.yaml")
        yaml = YAML()

        if not os.path.exists(path):
            self.add_profile()
            return

        with open(path) as f:
            data = yaml.load(f) or {}

        profiles = data.get("profiles", {})
        if not profiles:
            self.add_profile()
            return

        for name, entry in profiles.items():
            self.add_profile()
            self.populate_profile_from_entry(self.profile_widgets[-1], name, entry)

    # ------------------------------------------------------------
    # POPULATE PROFILE
    # ------------------------------------------------------------
    def populate_profile_from_entry(self, w, name, entry):
        # --- BASIC ---
        w["profile_name"].setText(name)
        w["planner"].setCurrentText(entry.get("planner_name", ""))
        w["mode"].setCurrentText(entry.get("mode", "Deployment"))

        # --- DEPLOYMENT ---
        if entry.get("mode") == "Deployment":
            w["lookup_table"].setCurrentText(entry.get("lookup_table", "").replace(".json", ""))
            w["lookup_algo"].setCurrentText(entry.get("lookup_algo", ""))
            w["builder_algo"].setCurrentText(entry.get("profile_builder_algo", ""))
            w["rate"].setText(str(entry.get("rate", 0)))

            w["speed_req"].setCurrentText(str(entry.get("speed_required", False)))
            if entry.get("speed_required"):
                w["speed_topic"].setText(entry.get("speed_topic", ""))

            w["intent_req"].setCurrentText(str(entry.get("intent_required", False)))
            if entry.get("intent_required"):
                w["intent_topic"].setText(entry.get("intent_topic", ""))

        if entry.get("mode") == "HIL":
            w["hil_algo"].setCurrentText(entry.get("hil_algo", "OPT_BAYESIAN"))
            w["hil_output"].setText(entry.get("hil_output_topic", ""))
            w["builder_algo"].setCurrentText(entry.get("profile_builder_algo", ""))
            # lookup_table / lookup_algo / rate are Deployment-only; not loaded for HIL.

            maximize = entry.get("hil_hyperparams", {}).get("maximize", True)
            w["hil_purpose"].setCurrentText("Maximization" if maximize else "Minimization")

            # 🔹 Rebuild hyperfields FIRST
            self.update_hil_hyperfields(
                w["hil_algo"].currentText(),
                w["hil_hyper_layout"],
                w["cma_rows"],
                w["bayes_rows"],
                w["hil_purpose"]
            )

            # 🔹 Apply the hyperparameter values into the dimension rows and
            # extra fields. We apply synchronously now AND again on the next
            # event-loop tick. The deferred re-apply is the important part: any
            # signal/timer that rebuilds the hyperfields right after load (e.g.
            # a hil_algo change or a first-time init) would otherwise reset the
            # dimension rows to their defaults. Because this re-apply is queued
            # AFTER add_profile's init timer (FIFO singleShot(0) ordering), the
            # loaded values always win.
            hyper = entry.get("hil_hyperparams", {})
            algo = w["hil_algo"].currentText()
            self._apply_hil_hyperparams(w, hyper, algo)
            QTimer.singleShot(
                0, lambda w=w, hyper=hyper, algo=algo: self._apply_hil_hyperparams(w, hyper, algo)
            )


        # --- COST FUNCTION ---
        if "cost_algo" in entry:
            w["cost_enable"].setCurrentText("Yes")
            w["cost_algo"].setCurrentText(entry.get("cost_algo", ""))
            w["cost_topic"].setText(entry.get("cost_topic", ""))
            w["cost_params"].setText(",".join(map(str, entry.get("cost_params", []))))

            # Clear default sensor rows
            # ---- CLEAR EXISTING SENSOR ROWS ----
            for hub_c, sensor_c in w["cost_sensors"]:
                hub_c.deleteLater()
                sensor_c.deleteLater()
            w["cost_sensors"].clear()

            # Also clear layout safely
            while w["cost_sensors_box"].count():
                item = w["cost_sensors_box"].takeAt(0)
                if item.layout():
                    while item.layout().count():
                        sub = item.layout().takeAt(0)
                        if sub.widget():
                            sub.widget().deleteLater()

            # ---- ADD SENSORS FROM YAML ----
            for hub, sensor in entry.get("sensors", []):
                row = QHBoxLayout()

                hub_combo = QComboBox()
                hub_combo.addItems(self.hubs.keys())
                hub_combo.setCurrentText(hub)

                sensor_combo = QComboBox()
                sensor_combo.addItems(self.hubs.get(hub, {}).get("sensors", []))
                sensor_combo.setCurrentText(sensor)

                row.addWidget(hub_combo)
                row.addWidget(sensor_combo)

                w["cost_sensors_box"].addLayout(row)
                w["cost_sensors"].append((hub_combo, sensor_combo))

            if "external_sensors_topic" in entry:
                w["ext_req"].setCurrentText("True")
                w["ext_topic"].setText(entry["external_sensors_topic"])

            if "additional_gait_marker_topic" in entry:
                w["gait_req"].setCurrentText("True")
                w["gait_topic"].setText(entry["additional_gait_marker_topic"])

            w["gait_skip"].setText(str(entry.get("gait_cycles_to_skip", 0)))
            w["gait_consider"].setText(str(entry.get("gait_cycles_to_consider", 1)))

    def _apply_hil_hyperparams(self, w, hyper, algo):
        """
        Populate the HIL dimension rows (CMA mean/bounds or Bayesian pbounds) and
        the extra hyperparameter widgets from a hil_hyperparams dict.

        Idempotent and safe to call repeatedly. populate_profile_from_entry calls
        it once synchronously and once more on the next event-loop tick, so any
        rebuild of the hyperfields triggered by a signal/timer immediately after
        load cannot leave the dimension rows blank. The algo guard prevents a
        stale deferred call from writing into a different algorithm's widgets.
        """
        if not hyper:
            return
        if w["hil_algo"].currentText() != algo:
            return  # selection changed since this was scheduled — skip

        if algo == "OPT_CMA_ES":
            means = hyper.get("mean", [])
            bounds = hyper.get("bounds", [])
            while len(w["cma_rows"]) < len(means):
                self.add_cma_dim(w["hil_hyper_layout"], w["cma_rows"])
            for i, (mean, bnd) in enumerate(zip(means, bounds)):
                mean_e, lb_e, ub_e = w["cma_rows"][i]
                mean_e.setText(str(mean))
                lb_e.setText(str(bnd[0]))
                ub_e.setText(str(bnd[1]))

        elif algo == "OPT_BAYESIAN":
            pbounds = hyper.get("pbounds", {})
            while len(w["bayes_rows"]) < len(pbounds):
                self.add_bayes_dim(w["hil_hyper_layout"], w["bayes_rows"])
            for idx, (lb, ub) in enumerate(pbounds.values()):
                lb_e, ub_e = w["bayes_rows"][idx]
                lb_e.setText(str(lb))
                ub_e.setText(str(ub))

        # Acquisition function FIRST, so the conditional xi/kappa field exists
        # (and is in hil_extra_hyper) before we try to populate it. Prefer the
        # canonical "kind" key, tolerating legacy "acquisition_function"/"acq_func".
        for label, widget in w.get("hil_extra_hyper", []):
            if label == "Acquisition Function" and isinstance(widget, QComboBox):
                for c in ("kind", "acquisition_function", "acq_func"):
                    if c in hyper:
                        widget.setCurrentText(str(hyper[c]))
                        break
                break

        # Flat extras (xi/kappa/init_points/max_iters/sigma/...). hil_extra_hyper
        # now reflects the active acquisition param, so only xi or kappa is set.
        for label, widget in w.get("hil_extra_hyper", []):
            if label in ("GP alpha", "GP n_restarts_optimizer"):
                continue
            key = self.HIL_LABEL_KEY_MAP.get(label)
            candidates = [key, label]
            if label == "Acquisition Function":
                candidates += ["kind", "acquisition_function", "acq_func"]
            value = None
            for c in candidates:
                if c and c in hyper:
                    value = hyper[c]
                    break
            if value is None:
                continue
            if isinstance(widget, QLineEdit):
                widget.setText(str(value))
            elif isinstance(widget, QComboBox):
                widget.setCurrentText(str(value))

        # GP params (nested under gp_params).
        gp = hyper.get("gp_params", {})
        for label, widget in w.get("hil_extra_hyper", []):
            if label == "GP alpha" and "alpha" in gp:
                widget.setText(str(gp["alpha"]))
            elif label == "GP n_restarts_optimizer" and "n_restarts_optimizer" in gp:
                widget.setText(str(gp["n_restarts_optimizer"]))

    # ---------------- EXISTING METHODS ----------------
    # add_profile(), update_mode_frames(), add_cma_dim(),
    # add_bayes_dim(), update_hil_hyperfields(), save_yaml()
    # 🔒 LEFT COMPLETELY UNCHANGED
    def add_profile(self):
        box = QGroupBox("Profile")
        box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QVBoxLayout(box)

        # ---------------- BASIC ----------------
        profile_name = QLineEdit()
        profile_name.setPlaceholderText("Profile name")
        layout.addWidget(QLabel("Profile Name"))
        layout.addWidget(profile_name)

        planner_combo = QComboBox()
        planner_combo.addItems(self.planner_names)
        layout.addWidget(QLabel("Planner Name"))
        layout.addWidget(planner_combo)

        mode_combo = QComboBox()
        mode_combo.addItems(["Deployment", "HIL"])
        layout.addWidget(QLabel("Mode"))
        layout.addWidget(mode_combo)

        # ================= COMMON (both Deployment & HIL) =================
        # profile_builder_algo is the only field shared by both modes, so it
        # lives outside the mode-specific frames and stays visible regardless of
        # the selected mode. (lookup_table / lookup_algo / rate are Deployment-only.)
        builder_algo = QComboBox()
        builder_dir = os.path.expanduser("~/exo_stack_resources/algo/builder")
        if os.path.exists(builder_dir):
            builder_algo.addItems([f.replace(".py", "") for f in os.listdir(builder_dir) if f.endswith(".py")])
        layout.addWidget(QLabel("Profile Builder Algorithm"))
        layout.addWidget(builder_algo)

        # ================= DEPLOYMENT (mode-specific) =================
        deploy_frame = QFrame()
        deploy_layout = QVBoxLayout(deploy_frame)
        deploy_layout.setContentsMargins(0, 0, 0, 0)

        speed_req = QComboBox()
        speed_req.addItems(["False", "True"])
        speed_topic = QLineEdit()
        speed_topic.setPlaceholderText("/speed_topic")
        speed_topic.setVisible(False)

        deploy_layout.addWidget(QLabel("Speed Required"))
        deploy_layout.addWidget(speed_req)
        deploy_layout.addWidget(speed_topic)

        intent_req = QComboBox()
        intent_req.addItems(["False", "True"])
        intent_topic = QLineEdit()
        intent_topic.setPlaceholderText("/intent_topic")
        intent_topic.setVisible(False)

        deploy_layout.addWidget(QLabel("Intent Required"))
        deploy_layout.addWidget(intent_req)
        deploy_layout.addWidget(intent_topic)

        lookup_table = QComboBox()
        lookup_dir = os.path.expanduser("~/exo_stack_resources/lookup_table")
        if os.path.exists(lookup_dir):
            lookup_table.addItems([f.replace(".json", "") for f in os.listdir(lookup_dir) if f.endswith(".json")])
        deploy_layout.addWidget(QLabel("Lookup Table"))
        deploy_layout.addWidget(lookup_table)

        lookup_algo = QComboBox()
        algo_dir = os.path.expanduser("~/exo_stack_resources/algo/lookup_algo")
        if os.path.exists(algo_dir):
            lookup_algo.addItems([f.replace(".py", "") for f in os.listdir(algo_dir) if f.endswith(".py")])
        deploy_layout.addWidget(QLabel("Lookup Algorithm"))
        deploy_layout.addWidget(lookup_algo)

        rate_edit = QLineEdit()
        rate_edit.setPlaceholderText("Rate (Hz)")
        deploy_layout.addWidget(QLabel("Rate"))
        deploy_layout.addWidget(rate_edit)

        layout.addWidget(deploy_frame)

        # ================= HIL =================
        hil_frame = QFrame()
        hil_layout = QVBoxLayout(hil_frame)
        hil_frame.setVisible(False)

        hil_algo_combo = QComboBox()
        hil_dir = os.path.expanduser("~/exo_stack_resources/algo/hil_optimizer")
        if os.path.exists(hil_dir):
            hil_algo_combo.addItems([f.replace(".py","") for f in os.listdir(hil_dir) if f.endswith(".py")])
        hil_layout.addWidget(QLabel("HIL Optimizer Algorithm"))
        hil_layout.addWidget(hil_algo_combo)

        hil_output_edit = QLineEdit()
        hil_output_edit.setPlaceholderText("/hil_output_topic")
        hil_layout.addWidget(QLabel("HIL Output Topic"))
        hil_layout.addWidget(hil_output_edit)

        purpose_combo = QComboBox()
        purpose_combo.addItems(["Maximization", "Minimization"])
        hil_layout.addWidget(QLabel("Purpose"))
        hil_layout.addWidget(purpose_combo)

        hyper_frame = QFrame()
        hyper_layout = QVBoxLayout(hyper_frame)
        hil_layout.addWidget(hyper_frame)

        cma_rows = []
        bayes_rows = []

        # Initialize Bayesian first-time render.
        # IMPORTANT: this fires on the next event-loop tick. If this profile was
        # populated from an existing YAML in the meantime, its hyperfields are
        # already built and filled, so we must NOT rebuild (which would wipe the
        # loaded values). We only build defaults when the layout is still empty.
        def init_hil_fields():
            if hyper_layout.count() > 0:
                return  # already built/populated (e.g. loaded from YAML)
            if hil_algo_combo.currentText() == "":
                hil_algo_combo.setCurrentText("OPT_BAYESIAN")
            self.update_hil_hyperfields(hil_algo_combo.currentText(), hyper_layout, cma_rows, bayes_rows, purpose_combo)

        QTimer.singleShot(0, init_hil_fields)
        hil_algo_combo.currentTextChanged.connect(lambda algo: self.update_hil_hyperfields(algo, hyper_layout, cma_rows, bayes_rows, purpose_combo))
        layout.addWidget(hil_frame)

        # ================= COST FUNCTION =================
        cost_enable = QComboBox()
        cost_enable.addItems(["No", "Yes"])
        layout.addWidget(QLabel("Define Cost Function"))
        layout.addWidget(cost_enable)

        cost_frame = QFrame()
        cost_layout = QVBoxLayout(cost_frame)
        cost_frame.setVisible(False)

        cost_algo = QComboBox()
        cost_dir = os.path.expanduser("~/exo_stack_resources/algo/cost")
        if os.path.exists(cost_dir):
            cost_algo.addItems([f.replace(".py", "") for f in os.listdir(cost_dir) if f.endswith(".py")])
        cost_layout.addWidget(QLabel("Cost Algorithm"))
        cost_layout.addWidget(cost_algo)

        cost_topic = QLineEdit()
        cost_topic.setPlaceholderText("/cost_topic")
        cost_layout.addWidget(QLabel("Cost Topic"))
        cost_layout.addWidget(cost_topic)

        cost_params = QLineEdit()
        cost_params.setPlaceholderText("Comma separated params")
        cost_layout.addWidget(QLabel("Cost Params"))
        cost_layout.addWidget(cost_params)

        sensors_rows = []
        sensors_box = QVBoxLayout()
        cost_layout.addWidget(QLabel("Sensors for Cost"))
        cost_layout.addLayout(sensors_box)


        def add_sensor_row():
            row = QHBoxLayout()
            hub_combo = QComboBox()
            hub_combo.addItems(self.hubs.keys())
            sensor_combo = QComboBox()

            def update_sensors():
                hub = hub_combo.currentText()
                sensor_combo.clear()
                sensor_combo.addItems(self.hubs.get(hub, {}).get("sensors", []))

            hub_combo.currentIndexChanged.connect(update_sensors)
            update_sensors()

            row.addWidget(hub_combo)
            row.addWidget(sensor_combo)
            sensors_box.addLayout(row)
            sensors_rows.append((hub_combo, sensor_combo))

        add_sensor_row()
        cost_layout.addLayout(sensors_box)
        add_sensor_btn = QPushButton("+ Add Sensor")
        add_sensor_btn.clicked.connect(add_sensor_row)
        cost_layout.addWidget(add_sensor_btn)

        ext_req = QComboBox()
        ext_req.addItems(["False", "True"])
        ext_topic = QLineEdit()
        ext_topic.setPlaceholderText("/external_sensors_topic")
        ext_topic.setVisible(False)
        cost_layout.addWidget(QLabel("External Sensors Used"))
        cost_layout.addWidget(ext_req)
        cost_layout.addWidget(ext_topic)

        gait_marker_req = QComboBox()
        gait_marker_req.addItems(["False", "True"])
        gait_marker_topic = QLineEdit()
        gait_marker_topic.setPlaceholderText("/additional_gait_marker_topic")
        gait_marker_topic.setVisible(False)
        cost_layout.addWidget(QLabel("Additional Gait Marker"))
        cost_layout.addWidget(gait_marker_req)
        cost_layout.addWidget(gait_marker_topic)

        gait_skip = QLineEdit()
        gait_consider = QLineEdit()
        gait_skip.setPlaceholderText("Cycles to skip")
        gait_consider.setPlaceholderText("Cycles to consider")
        cost_layout.addWidget(QLabel("Gait Cycles to Skip"))
        cost_layout.addWidget(gait_skip)
        cost_layout.addWidget(QLabel("Gait Cycles to Consider"))
        cost_layout.addWidget(gait_consider)

        layout.addWidget(cost_frame)

        # ---------------- SIGNALS ----------------
        speed_req.currentTextChanged.connect(lambda t: speed_topic.setVisible(t == "True"))
        intent_req.currentTextChanged.connect(lambda t: intent_topic.setVisible(t == "True"))
        cost_enable.currentTextChanged.connect(lambda t: cost_frame.setVisible(t == "Yes"))
        ext_req.currentTextChanged.connect(lambda t: ext_topic.setVisible(t == "True"))
        gait_marker_req.currentTextChanged.connect(lambda t: gait_marker_topic.setVisible(t == "True"))
        mode_combo.currentTextChanged.connect(lambda t: self.update_mode_frames(t, deploy_frame, hil_frame))

        # ---------------- STORE ----------------
        wdict = {
            "container": box,
            "profile_name": profile_name,
            "planner": planner_combo,
            "mode": mode_combo,
            "speed_req": speed_req,
            "speed_topic": speed_topic,
            "intent_req": intent_req,
            "intent_topic": intent_topic,
            "lookup_table": lookup_table,
            "lookup_algo": lookup_algo,
            "builder_algo": builder_algo,
            "rate": rate_edit,
            "hil_algo": hil_algo_combo,
            "hil_output": hil_output_edit,
            "hil_purpose": purpose_combo,
            "hil_hyper_layout": hyper_layout,
            "cma_rows": cma_rows,
            "bayes_rows": bayes_rows,
            "cost_enable": cost_enable,
            "cost_algo": cost_algo,
            "cost_topic": cost_topic,
            "cost_params": cost_params,
            "cost_sensors": sensors_rows,
            "cost_sensors_box": sensors_box,
            "ext_req": ext_req,
            "ext_topic": ext_topic,
            "gait_req": gait_marker_req,
            "gait_topic": gait_marker_topic,
            "gait_skip": gait_skip,
            "gait_consider": gait_consider,
            "hil_extra_hyper": []  # will store extra widgets
        }
        self.profile_widgets.append(wdict)

        # ---------------- REMOVE PROFILE ----------------
        remove_btn = QPushButton("Remove Profile")
        remove_btn.setProperty("role", "danger")
        remove_btn.clicked.connect(lambda _=False, w=wdict: self.remove_profile(w))
        layout.addWidget(remove_btn)

        self.profile_column.addWidget(box)

    # ----------------- REMOVE PROFILE -----------------
    def remove_profile(self, w):
        box = w.get("container")
        if box is not None:
            self.profile_column.removeWidget(box)
            box.setParent(None)
            box.deleteLater()
        if w in self.profile_widgets:
            self.profile_widgets.remove(w)

    # ----------------- MODE SWITCH -----------------
    def update_mode_frames(self, mode, deploy_frame, hil_frame):
        deploy_frame.setVisible(mode=="Deployment")
        hil_frame.setVisible(mode=="HIL")
        if mode == "HIL":
            for w in self.profile_widgets:
                if w["mode"].currentText() == "HIL" and w["hil_algo"].currentText() == "":
                    w["hil_algo"].setCurrentText("OPT_BAYESIAN")
                    self.update_hil_hyperfields("OPT_BAYESIAN", w["hil_hyper_layout"], w["cma_rows"], w["bayes_rows"], w["hil_purpose"])

    # ----------------- CMA / BAYESIAN DIM ROWS -----------------
    def add_cma_dim(self, layout, cma_rows, row_index=None, mean_val="0.0", lb_val="0", ub_val="1"):
        if not cma_rows:
            header = QHBoxLayout()
            header.addWidget(QLabel("Mean"))
            header.addWidget(QLabel("Lower Bound"))
            header.addWidget(QLabel("Upper Bound"))
            layout.insertLayout(0, header)
        row = QHBoxLayout()
        mean_edit = QLineEdit(mean_val)
        lb_edit = QLineEdit(lb_val)
        ub_edit = QLineEdit(ub_val)
        row.addWidget(mean_edit)
        row.addWidget(lb_edit)
        row.addWidget(ub_edit)
        layout.insertLayout(1 + len(cma_rows), row)
        cma_rows.append((mean_edit, lb_edit, ub_edit))

    def add_bayes_dim(self, layout, bayes_rows, row_index=None, lb_val="0", ub_val="1"):
        if not bayes_rows:
            header = QHBoxLayout()
            header.addWidget(QLabel("Lower Bound"))
            header.addWidget(QLabel("Upper Bound"))
            layout.insertLayout(0, header)
        row = QHBoxLayout()
        lb_edit = QLineEdit(lb_val)
        ub_edit = QLineEdit(ub_val)
        row.addWidget(lb_edit)
        row.addWidget(ub_edit)
        layout.insertLayout(1 + len(bayes_rows), row)
        bayes_rows.append((lb_edit, ub_edit))

    # ----------------- UPDATE HIL HYPERFIELDS -----------------
    def update_hil_hyperfields(self, algo, container_layout, cma_rows, bayes_rows, purpose_combo):
        # 1️⃣ Clear previous widgets & layouts safely
        while container_layout.count():
            item = container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub_item = item.layout().takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()
                item.layout().setParent(None)
                item.layout().deleteLater()

        cma_rows.clear()
        bayes_rows.clear()
        extra_widgets = []

        # 2️⃣ Build new widgets
        if algo == "OPT_CMA_ES":
            self.add_cma_dim(container_layout, cma_rows)
            add_dim_btn = QPushButton("+ Add Dimension")
            add_dim_btn.clicked.connect(lambda: self.add_cma_dim(container_layout, cma_rows))
            container_layout.addWidget(add_dim_btn)

            for label, default in [("sigma", "0.5"), ("max_generations", "2"), ("population_size", "9"), ("n_max_resampling", "1")]:
                edit = QLineEdit(default)
                edit.setPlaceholderText(label)
                container_layout.addWidget(QLabel(label))
                container_layout.addWidget(edit)
                extra_widgets.append((label, edit))

        elif algo == "OPT_BAYESIAN":
            self.add_bayes_dim(container_layout, bayes_rows)
            add_dim_btn = QPushButton("+ Add Dimension")
            add_dim_btn.clicked.connect(lambda: self.add_bayes_dim(container_layout, bayes_rows))
            container_layout.addWidget(add_dim_btn)

            # Universal Bayesian fields (valid OPT_BAYESIAN constructor args).
            init_points_edit = QLineEdit("5")
            init_points_edit.setPlaceholderText("init_points")
            container_layout.addWidget(QLabel("init_points (random seed candidates)"))
            container_layout.addWidget(init_points_edit)

            max_iters_edit = QLineEdit("30")
            max_iters_edit.setPlaceholderText("max_iters")
            container_layout.addWidget(QLabel("max_iters (GP iters after init_points)"))
            container_layout.addWidget(max_iters_edit)

            # Acquisition function selector — chosen BEFORE its specific param.
            acq_func = QComboBox()
            acq_func.addItems(["ei", "ucb", "poi"])
            container_layout.addWidget(QLabel("Acquisition Function"))
            container_layout.addWidget(acq_func)

            # Acquisition-specific params. xi is used by ei/poi, kappa by ucb
            # (see OPT_BAYESIAN: UtilityFunction(kind, xi) vs (kind, kappa)).
            # Both widgets persist so toggling keeps the last-entered value; only
            # the relevant one is shown AND saved.
            xi_label = QLabel("xi (ei / poi)")
            xi_edit = QLineEdit("0.02")
            xi_edit.setPlaceholderText("xi")
            kappa_label = QLabel("kappa (ucb)")
            kappa_edit = QLineEdit("2.5")
            kappa_edit.setPlaceholderText("kappa")
            container_layout.addWidget(xi_label)
            container_layout.addWidget(xi_edit)
            container_layout.addWidget(kappa_label)
            container_layout.addWidget(kappa_edit)

            # GP regressor params (universal) -> saved nested under "gp_params".
            gp_alpha = QLineEdit("0.01")
            gp_alpha.setPlaceholderText("GP alpha")
            container_layout.addWidget(QLabel("GP alpha"))
            container_layout.addWidget(gp_alpha)

            gp_nrestart = QLineEdit("5")
            gp_nrestart.setPlaceholderText("GP n_restarts_optimizer")
            container_layout.addWidget(QLabel("GP n_restarts_optimizer"))
            container_layout.addWidget(gp_nrestart)

            base_extra = [
                ("init_points", init_points_edit),
                ("max_iters", max_iters_edit),
                ("Acquisition Function", acq_func),
                ("GP alpha", gp_alpha),
                ("GP n_restarts_optimizer", gp_nrestart),
            ]

            def apply_acq(kind, _self=self, _cl=container_layout, _extra=extra_widgets):
                is_ucb = (kind == "ucb")
                xi_label.setVisible(not is_ucb)
                xi_edit.setVisible(not is_ucb)
                kappa_label.setVisible(is_ucb)
                kappa_edit.setVisible(is_ucb)
                active = ("kappa", kappa_edit) if is_ucb else ("xi", xi_edit)
                # Keep extra_widgets (and the stored ref) in sync so save/load
                # only ever see the acquisition-relevant param.
                _extra.clear()
                _extra.extend(base_extra + [active])
                for ww in _self.profile_widgets:
                    if ww["hil_hyper_layout"] == _cl:
                        ww["hil_extra_hyper"] = list(_extra)

            acq_func.currentTextChanged.connect(apply_acq)
            apply_acq(acq_func.currentText())

        # 3️⃣ Save reference to the new widgets
        for w in self.profile_widgets:
            if w["hil_hyper_layout"] == container_layout:
                w["hil_extra_hyper"] = list(extra_widgets)


    # ----------------- SAVE YAML -----------------
    def save_yaml(self):
        yaml = YAML()
        data = {"profiles": {}}

        for w in self.profile_widgets:
            name = w["profile_name"].text().strip()
            if not name:
                continue

            mode = w["mode"].currentText()
            entry = {
                "planner_name": w["planner"].currentText(),
                "mode": mode
            }

            if mode == "Deployment":
                entry["lookup_table"] = w["lookup_table"].currentText() + ".json"
                entry["lookup_algo"] = w["lookup_algo"].currentText()
                entry["profile_builder_algo"] = w["builder_algo"].currentText()
                entry["rate"] = int(w["rate"].text() or 0)
                entry["speed_required"] = w["speed_req"].currentText() == "True"
                if entry["speed_required"]:
                    entry["speed_topic"] = normalize_topic(w["speed_topic"].text())
                entry["intent_required"] = w["intent_req"].currentText() == "True"
                if entry["intent_required"]:
                    entry["intent_topic"] = normalize_topic(w["intent_topic"].text())

            elif mode == "HIL":
                entry["hil_algo"] = w["hil_algo"].currentText()
                entry["hil_output_topic"] = normalize_topic(w["hil_output"].text())
                entry["profile_builder_algo"] = w["builder_algo"].currentText()
                # NOTE: lookup_table / lookup_algo / rate are Deployment-only and
                # are intentionally NOT written for HIL profiles.
                maximize = w["hil_purpose"].currentText() == "Maximization"

                hil_hyper = {}

                # Preserve the number's int/float style based on how it is
                # written in the field: text containing a decimal point or
                # exponent is kept as a float (e.g. 50.0, 0.02), otherwise it is
                # written as an int (e.g. 20, 10). This gives a faithful
                # round-trip of hand-authored YAML (mean stays 50.0, bounds 10).
                def _num(text, default="0"):
                    t = (text or "").strip() or str(default)
                    try:
                        if any(c in t for c in (".", "e", "E")):
                            return float(t)
                        return int(t)
                    except ValueError:
                        try:
                            return float(t)
                        except ValueError:
                            return 0

                if entry["hil_algo"] == "OPT_CMA_ES":
                    mean_list, bounds_list = [], []
                    for mean_e, lb_e, ub_e in w["cma_rows"]:
                        mean_list.append(_num(mean_e.text(), "0"))
                        bounds_list.append([_num(lb_e.text(), "0"), _num(ub_e.text(), "1")])

                    hil_hyper["mean"] = mean_list
                    hil_hyper["bounds"] = bounds_list
                    hil_hyper["maximize"] = maximize

                elif entry["hil_algo"] == "OPT_BAYESIAN":
                    pbounds = {}
                    for idx, (lb_e, ub_e) in enumerate(w["bayes_rows"]):
                        pbounds[f"param{idx+1}"] = [
                            _num(lb_e.text(), "0"),
                            _num(ub_e.text(), "1")
                        ]

                    hil_hyper["pbounds"] = pbounds
                    hil_hyper["maximize"] = maximize

                # Read the extra hyperparameter widgets into the dict. For
                # Bayesian, w["hil_extra_hyper"] contains init_points, max_iters,
                # the acquisition function (saved under its real key "kind"), the
                # active acquisition param (xi OR kappa), and the two GP fields.
                # GP fields are collected into a nested "gp_params" dict; every
                # other key is a flat, valid optimizer constructor argument, so
                # ExoStack's OptimizerClass(**hil_hyperparams) splat is safe.
                gp_hyper = {}
                for label, widget in w.get("hil_extra_hyper", []):
                    if label == "GP alpha":
                        if isinstance(widget, QLineEdit):
                            gp_hyper["alpha"] = _num(widget.text(), "0")
                        continue
                    if label == "GP n_restarts_optimizer":
                        if isinstance(widget, QLineEdit):
                            gp_hyper["n_restarts_optimizer"] = _num(widget.text(), "0")
                        continue

                    key = self.HIL_LABEL_KEY_MAP.get(label)
                    if not key:
                        continue

                    if isinstance(widget, QComboBox):
                        hil_hyper[key] = widget.currentText()
                    elif isinstance(widget, QLineEdit):
                        hil_hyper[key] = _num(widget.text(), "0")

                if gp_hyper:
                    hil_hyper["gp_params"] = gp_hyper

                entry["hil_hyperparams"] = hil_hyper



            # Cost Function
            if w["cost_enable"].currentText() == "Yes":
                entry["cost_algo"] = w["cost_algo"].currentText()
                entry["cost_topic"] = normalize_topic(w["cost_topic"].text())
                entry["cost_params"] = [float(x.strip()) for x in w["cost_params"].text().split(",") if x.strip()]
                sensors_list = []
                for hub_c, sensor_c in w["cost_sensors"]:
                    sensors_list.append([hub_c.currentText(), sensor_c.currentText()])
                entry["sensors"] = sensors_list
                if w["ext_req"].currentText() == "True":
                    entry["external_sensors_topic"] = normalize_topic(w["ext_topic"].text())
                if w["gait_req"].currentText() == "True":
                    entry["additional_gait_marker_topic"] = normalize_topic(w["gait_topic"].text())
                entry["gait_cycles_to_skip"] = int(w["gait_skip"].text() or 0)
                entry["gait_cycles_to_consider"] = int(w["gait_consider"].text() or 1)

            data["profiles"][name] = entry

        save_path = os.path.expanduser("~/exo_stack_resources/config/profile.yaml")
        with open(save_path, "w") as f:
            yaml.dump(data, f)