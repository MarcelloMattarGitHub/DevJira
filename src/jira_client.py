"""Cliente mínimo da API REST do Jira Cloud."""
import requests

PAGE_SIZE = 100


class JiraError(Exception):
    pass


class JiraClient:
    def __init__(self, url: str, email: str, token: str):
        url = url.strip().rstrip("/")
        if not url.startswith("http"):
            url = "https://" + url
        self.base = url
        self.session = requests.Session()
        self.session.auth = (email.strip(), token.strip())
        self.session.headers["Accept"] = "application/json"

    def _get(self, path: str, **params):
        try:
            r = self.session.get(f"{self.base}/rest/api/3{path}", params=params, timeout=30)
        except requests.RequestException as e:
            raise JiraError(f"Falha de conexão: {e}") from e
        if r.status_code == 401:
            raise JiraError("Credenciais inválidas (verifique e-mail e API token).")
        if r.status_code == 403:
            raise JiraError("Sem permissão para listar usuários.")
        if not r.ok:
            raise JiraError(f"Jira respondeu {r.status_code}: {r.text[:200]}")
        return r.json()

    def get_users(self, only_active: bool = True) -> list[dict]:
        """Todas as pessoas (contas Atlassian) do site, ordenadas por nome."""
        self._get("/myself")  # valida as credenciais (sem isso o Jira responde como anônimo)
        users, start = [], 0
        while True:
            page = self._get("/users/search", startAt=start, maxResults=PAGE_SIZE)
            if not page:
                break
            users.extend(page)
            start += len(page)
        users = [
            u for u in users
            if u.get("accountType") == "atlassian" and (u.get("active") or not only_active)
        ]
        return sorted(users, key=lambda u: (u.get("displayName") or "").lower())

    def get_worked_hours(self, account_id: str, start: str, end: str) -> list[dict]:
        """Horas lançadas (worklogs) da pessoa em [start, end) — datas 'YYYY-MM-DD'.

        Retorna uma lista de {key, summary, seconds, dates}, uma por issue, ordenada por horas.
        """
        jql = (f'worklogAuthor = "{account_id}" AND worklogDate >= "{start}" '
               f'AND worklogDate < "{end}"')
        issues, token = [], None
        while True:
            params = {"jql": jql, "fields": "summary", "maxResults": 100}
            if token:
                params["nextPageToken"] = token
            page = self._get("/search/jql", **params)
            issues.extend(page.get("issues", []))
            token = page.get("nextPageToken")
            if page.get("isLast", True) or not token:
                break

        result = []
        for issue in issues:
            seconds, offset, dates = 0, 0, set()
            while True:
                wl = self._get(f"/issue/{issue['key']}/worklog", startAt=offset, maxResults=1000)
                for w in wl.get("worklogs", []):
                    # 'started' vem como 2026-10-04T10:00:00.000-0300; a data é o que importa
                    if (w.get("author", {}).get("accountId") == account_id
                            and start <= w["started"][:10] < end):
                        seconds += w.get("timeSpentSeconds", 0)
                        dates.add(w["started"][:10])
                offset += len(wl.get("worklogs", []))
                if not wl.get("worklogs") or offset >= wl.get("total", 0):
                    break
            if seconds:
                result.append({"key": issue["key"],
                               "summary": issue["fields"].get("summary", ""),
                               "seconds": seconds, "dates": sorted(dates)})
        return sorted(result, key=lambda r: -r["seconds"])
