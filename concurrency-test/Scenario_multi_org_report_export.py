from locust import HttpUser, TaskSet, task, between
import random
import time
import base64

REQUEST_TIMEOUT = 30
USER_STAGGER_MAX = 2.0
CLOSE_DELAY_BETWEEN_DELETES = 0.3
TASK_WEIGHT_OPEN_VS = 3
TASK_WEIGHT_EXPORT_VS = 2
TASK_WEIGHT_CHECK_EXPORT = 4
TASK_WEIGHT_LIST_SCHEDULE = 3
TASK_WEIGHT_CREATE_SCHEDULE = 1
TASK_WEIGHT_CLOSE_VS = 1


def encode_string(s: str) -> str:
    b = s.encode("utf-8")
    return base64.b64encode(b).decode("utf-8")


class MultiOrgExportAndScheduleTasks(TaskSet):
    """
    多组织导出与调度场景：
    - 打开 Viewsheet
    - 导出 Viewsheet（PDF/Excel/CSV）
    - 检查导出状态
    - 查看调度任务列表
    - 创建调度任务
    - 关闭 Viewsheet
    """

    org_viewsheets = {
        "org-ci1": [
            ("1^128^__NULL__^Examples/Sales Summary^org-ci1", 3),
            ("1^128^__NULL__^Examples/Return Analysis^org-ci1", 2),
            ("1^128^__NULL__^Examples/Construction Dashboard^org-ci1", 2),
            ("1^128^__NULL__^Examples/Call Center Monitoring^org-ci1", 2),
            ("1^128^__NULL__^Examples/Census^org-ci1", 1),
            ("1^128^__NULL__^Examples/Projection^org-ci1", 2),
            ("1^128^__NULL__^Examples/Hurricane^org-ci1", 1),
        ],
        "org-ci2": [
            ("1^128^__NULL__^Examples/Sales Summary^org-ci2", 3),
            ("1^128^__NULL__^Examples/Return Analysis^org-ci2", 2),
            ("1^128^__NULL__^Examples/Construction Dashboard^org-ci2", 2),
            ("1^128^__NULL__^Examples/Call Center Monitoring^org-ci2", 2),
            ("1^128^__NULL__^Examples/Census^org-ci2", 1),
            ("1^128^__NULL__^Examples/Projection^org-ci2", 2),
            ("1^128^__NULL__^Examples/Hurricane^org-ci2", 1),
        ],
    }

    vs_identifier = None
    current_vs_asset = None
    export_jobs = []

    @task(TASK_WEIGHT_OPEN_VS)
    def open_viewsheet(self):
        """打开 Viewsheet"""
        org_id = getattr(self.user, "org_id", None)
        viewsheets = self.org_viewsheets.get(org_id)
        if not viewsheets:
            viewsheets = next(iter(self.org_viewsheets.values()))

        # 按权重随机选择 Viewsheet
        vs_info = random.choices(
            viewsheets,
            weights=[v[1] for v in viewsheets],
            k=1,
        )[0]

        self.current_vs_asset = vs_info[0]

        vs_body = {"asset": self.current_vs_asset}
        resp = self.client.post(
            "/api/public/viewsheets/open",
            json=vs_body,
            headers=self.user.headers,
            timeout=REQUEST_TIMEOUT,
        )

        if resp.status_code == 201:
            try:
                vs_json = resp.json()
                self.vs_identifier = vs_json.get("identifier")
            except ValueError:
                self.vs_identifier = None

        time.sleep(random.uniform(0.5, 1.5))

    @task(TASK_WEIGHT_EXPORT_VS)
    def export_viewsheet(self):
        """导出 Viewsheet"""
        if not self.vs_identifier:
            self.open_viewsheet()
            if not self.vs_identifier:
                return

        # 随机选择导出格式
        export_formats = [1, 2, 4]  # 1=PDF, 2=Excel, 4=CSV
        export_format = random.choice(export_formats)

        # 构建导出 URL（基于实际的 API 路径）
        # /export/viewsheet/{path}?format={format}
        vs_path = self.current_vs_asset.replace("^", "/")
        
        params = {
            "format": export_format,
            "match": "false",
            "expandSelections": "false",
        }

        resp = self.client.get(
            f"/export/viewsheet/{vs_path}",
            params=params,
            headers=self.user.headers,
            timeout=REQUEST_TIMEOUT,
            name="/export/viewsheet/[path]",
        )

        # 导出通常返回文件流或任务ID
        if resp.status_code == 200:
            # 成功导出
            pass
        elif resp.status_code == 202:
            # 异步导出，返回任务ID
            try:
                result = resp.json()
                job_id = result.get("jobId")
                if job_id:
                    self.export_jobs.append({
                        "jobId": job_id,
                        "vsIdentifier": self.vs_identifier,
                    })
                    if len(self.export_jobs) > 10:
                        self.export_jobs.pop(0)
            except ValueError:
                pass

        time.sleep(random.uniform(0.5, 2.0))

    @task(TASK_WEIGHT_CHECK_EXPORT)
    def check_export_status(self):
        """检查导出状态"""
        if not self.vs_identifier:
            return

        # 使用 /export/check/{runtimeId} 检查导出状态
        encoded_id = encode_string(self.vs_identifier)
        
        resp = self.client.get(
            f"/export/check/{encoded_id}",
            headers=self.user.headers,
            timeout=REQUEST_TIMEOUT,
            name="/export/check/[runtimeId]",
        )

        if resp.status_code in (404, 410):
            self.vs_identifier = None

        time.sleep(random.uniform(0.3, 1.0))

    @task(TASK_WEIGHT_LIST_SCHEDULE)
    def list_schedule_tasks(self):
        """查看调度任务列表"""
        org_id = getattr(self.user, "org_id", None)

        params = {
            "selectString": "",
            "filter": "",
        }

        resp = self.client.post(
            "/api/portal/scheduledTasks",
            params=params,
            headers=self.user.headers,
            timeout=REQUEST_TIMEOUT,
        )

        if resp.status_code == 200:
            try:
                result = resp.json()
                tasks = result.get("tasks", [])
                # 可以记录任务信息供后续操作
            except ValueError:
                pass

        time.sleep(random.uniform(0.3, 1.0))

    @task(TASK_WEIGHT_CREATE_SCHEDULE)
    def create_schedule_task(self):
        """创建调度任务（低频操作）"""
        if random.random() > 0.3:  # 只有30%概率创建
            return

        org_id = getattr(self.user, "org_id", None)
        viewsheets = self.org_viewsheets.get(org_id)
        if not viewsheets:
            return

        vs_info = random.choice(viewsheets)
        vs_asset = vs_info[0]

        # 构建调度任务数据（基于实际的 API 结构）
        schedule_data = {
            "name": f"Auto_Schedule_{int(time.time())}_{random.randint(1000, 9999)}",
            "taskType": "viewsheet",
            "viewsheet": vs_asset,
            "startTime": int(time.time() * 1000),
            "timeZone": "America/New_York",
            "enabled": True,
        }

        # 注意：实际的创建调度任务 API 可能在 /api/portal/schedule/task
        resp = self.client.post(
            "/api/portal/schedule/task",
            json=schedule_data,
            headers=self.user.headers,
            timeout=REQUEST_TIMEOUT,
        )

        time.sleep(random.uniform(0.5, 1.5))

    @task(TASK_WEIGHT_CLOSE_VS)
    def close_viewsheet(self):
        """关闭 Viewsheet（低频操作）"""
        if random.random() > 0.2:
            return

        if self.vs_identifier:
            self.client.delete(
                f"/api/public/viewsheets/open/{self.vs_identifier}",
                headers=self.user.headers,
                timeout=REQUEST_TIMEOUT,
            )
            self.vs_identifier = None
            time.sleep(CLOSE_DELAY_BETWEEN_DELETES)

        self.current_vs_asset = None
        self.export_jobs = []


class MultiOrgExportUser(HttpUser):
    """
    Multi-org 导出与调度用户
    """

    tasks = [MultiOrgExportAndScheduleTasks]
    wait_time = between(1, 5)

    org_accounts = [
        ("org-ci1", "ci1", "success123", 1),
        ("org-ci2", "ci2", "success123", 1),
    ]

    def on_start(self):
        time.sleep(random.uniform(0, USER_STAGGER_MAX))

        org_id, username, password, _ = random.choices(
            self.org_accounts,
            weights=[o[3] for o in self.org_accounts],
            k=1,
        )[0]

        self.org_id = org_id
        self.username = username
        self.password = password

        resp = self.client.post(
            "/api/public/login",
            json={"username": self.username, "orgID": self.org_id, "password": self.password},
        )

        print(f"[LOGIN] org={self.org_id}, user={self.username}, status={resp.status_code}, body={resp.text}")

        if resp.status_code == 200:
            try:
                token = resp.json().get("token")
                self.headers = {"x-inetsoft-api-token": token}
            except ValueError as e:
                print(f"[LOGIN] Failed to parse login JSON for org={self.org_id}: {e}")
                self.headers = {}
        else:
            self.headers = {}


if __name__ == "__main__":
    import os
    os.system("locust -f Scenario_multi_org_export_schedule.py")