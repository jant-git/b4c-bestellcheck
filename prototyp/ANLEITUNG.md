# Prototyp: Start, Testlauf, Freigabe, Aufräumen

Projekt `b4c-bestellcheck-hs26` (Projektnummer 975058578240), Region `europe-west6`, Rechnungskonto «Billing Account for Education».
Alle Befehle aus dem Ordner, der `kleinklasse-automation/` enthält. **Daten synthetisch.**
Für Projektverwaltung (Aufbau, Zugang, Aufräumen). Wer den Prototyp nur nutzt: [`../NUTZUNG.md`](../NUTZUNG.md).

## A Lokal (ohne Cloud, 1 Sekunde)

```bash
cd kleinklasse-automation/prototyp
python3 -m unittest -v test_regeln        # 10 Tests der Regeln
python3 lokal_lauf.py 2026-11-09          # Montag vor der Störung: S6 wird vorbereitet
python3 lokal_lauf.py 2026-11-16          # Störungswoche
python3 lokal_lauf.py 2026-11-02          # Cookies nicht gezählt: gelb
```
Lokal rechnet noch die Python-Bereinigung `job/bereinigen.py`. In der Cloud macht das seit SW11 dbt (`job/transform/`).
Dass beide dasselbe ergeben, zeigt Abfrage 8 in `abfragen.sql`.

dbt-Projekt lokal auf Fehler prüfen (ohne BigQuery, braucht Python ≤ 3.13 und `pip install dbt-bigquery`):
```bash
cd kleinklasse-automation/prototyp/job/transform
DBT_PROJECT=b4c-bestellcheck-hs26 dbt parse --profiles-dir .
```

## B Aufbau in Google Cloud (einmalig)

```bash
P=b4c-bestellcheck-hs26
R=europe-west6

# 1 APIs (nur aus der Liste in CLAUDE.md)
gcloud services enable cloudresourcemanager.googleapis.com serviceusage.googleapis.com iam.googleapis.com \
  storage.googleapis.com bigquery.googleapis.com run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com workflows.googleapis.com workflowexecutions.googleapis.com \
  cloudscheduler.googleapis.com logging.googleapis.com monitoring.googleapis.com --project=$P

# 2 Daten: Bucket, 5 synthetische CSV, BigQuery-Dataset
gcloud storage buckets create gs://$P-daten --location=$R --uniform-bucket-level-access --project=$P
gcloud storage cp kleinklasse-automation/prototyp/daten/*.csv gs://$P-daten/daten/ --project=$P
bq mk --location=$R --project_id=$P --dataset b4c_bestellcheck

# 3 Service-Accounts (Least Privilege)
gcloud iam service-accounts create b4c-job-sa --display-name="B4C Wochenlauf (Job)" --project=$P
gcloud iam service-accounts create b4c-workflow-sa --display-name="B4C Bestellcheck (Workflow)" --project=$P
#   Job: BigQuery lesen/schreiben, Bucket nur lesen
gcloud projects add-iam-policy-binding $P --member="serviceAccount:b4c-job-sa@$P.iam.gserviceaccount.com" --role="roles/bigquery.dataEditor"
gcloud projects add-iam-policy-binding $P --member="serviceAccount:b4c-job-sa@$P.iam.gserviceaccount.com" --role="roles/bigquery.jobUser"
gcloud storage buckets add-iam-policy-binding gs://$P-daten --member="serviceAccount:b4c-job-sa@$P.iam.gserviceaccount.com" --role="roles/storage.objectViewer"
#   Workflow: Schranke und Anfrage in BigQuery, Logs schreiben, Job-Status lesen
gcloud projects add-iam-policy-binding $P --member="serviceAccount:b4c-workflow-sa@$P.iam.gserviceaccount.com" --role="roles/bigquery.dataEditor"
gcloud projects add-iam-policy-binding $P --member="serviceAccount:b4c-workflow-sa@$P.iam.gserviceaccount.com" --role="roles/bigquery.jobUser"
gcloud projects add-iam-policy-binding $P --member="serviceAccount:b4c-workflow-sa@$P.iam.gserviceaccount.com" --role="roles/logging.logWriter"
gcloud projects add-iam-policy-binding $P --member="serviceAccount:b4c-workflow-sa@$P.iam.gserviceaccount.com" --role="roles/run.viewer"
#   Build: Das Compute-Standardkonto (Editor) baut. Die Rolle run.builder aus Lektion 1 war hier nicht nötig.

# 4 Job bauen und anlegen (Pfad relativ zum Repo-Hauptordner)
gcloud artifacts repositories create cloud-run-source-deploy --repository-format=docker --location=$R --project=$P
gcloud run jobs deploy b4c-wochenlauf --source kleinklasse-automation/prototyp/job --region=$R --project=$P \
  --service-account=b4c-job-sa@$P.iam.gserviceaccount.com --set-env-vars=BUCKET=$P-daten \
  --memory=1Gi --cpu=1 --task-timeout=10m --max-retries=0     # 1 GiB seit SW11 (dbt im Container)
#   Workflow darf genau diesen Job mit Parametern starten (Overrides brauchen Cloud Run Developer)
gcloud run jobs add-iam-policy-binding b4c-wochenlauf --region=$R --project=$P \
  --member="serviceAccount:b4c-workflow-sa@$P.iam.gserviceaccount.com" --role="roles/run.developer"

# 5 Workflow
gcloud workflows deploy b4c-bestellcheck --source=kleinklasse-automation/prototyp/workflow.yaml --location=$R --project=$P \
  --service-account=b4c-workflow-sa@$P.iam.gserviceaccount.com --call-log-level=log-all-calls
```

**Alarm bei Fehlschlag (seit SW11 angelegt, 23.11.2026).** gcloud bräuchte dafür die Komponenten `alpha`/`beta`;
wir nutzen stattdessen die REST-API von Cloud Monitoring mit dem eigenen Login (nichts zu installieren).
```bash
TOKEN=$(gcloud auth print-access-token)
# 1 E-Mail-Kanal (gibt "name": ".../notificationChannels/<ID>" zurück)
curl -X POST "https://monitoring.googleapis.com/v3/projects/$P/notificationChannels" \
  -H "Authorization: Bearer $TOKEN" -H "x-goog-user-project: $P" -H "Content-Type: application/json" \
  -d '{"type":"email","displayName":"B4C Alarm","labels":{"email_address":"ADRESSE"}}'
# 2 alarm-fehlschlag.yaml als JSON (z. B. mit Python und PyYAML), CHANNEL_ID durch den vollen Kanalnamen ersetzen, dann:
curl -X POST "https://monitoring.googleapis.com/v3/projects/$P/alertPolicies" \
  -H "Authorization: Bearer $TOKEN" -H "x-goog-user-project: $P" -H "Content-Type: application/json; charset=utf-8" \
  --data-binary @richtlinie.json
```
Angelegt: Kanal `B4C Alarm` (ID 17558113069386582374), Richtlinie `b4c-bestellcheck fehlgeschlagen`
(ID 12156258945515208134). **Nur beschrieben, nicht angelegt:** die Hinweis-Mail `alarm-hinweis.yaml`
(«Freigabe nötig», Eskalation). Diese Hinweise stehen als `b4c_ereignis` in Cloud Logging, und
`freigeben.py --zeigen` zeigt die offene Anfrage.

## B2 Zugang für Teammitglieder (pro Person, ZHAW-Konto)

Ansehen, Abfragen in BigQuery, Lauf starten und freigeben. Kein Löschen, kein Umbauen.
```bash
M=user:VORNAME.NAME@students.zhaw.ch     # bzw. das Kürzel-Konto, z. B. user:abcd1234@students.zhaw.ch
gcloud projects add-iam-policy-binding $P --member="$M" --role="roles/viewer" --condition=None
gcloud projects add-iam-policy-binding $P --member="$M" --role="roles/bigquery.jobUser" --condition=None
gcloud projects add-iam-policy-binding $P --member="$M" --role="roles/workflows.invoker" --condition=None
```
Zugang wieder entziehen: dieselben Befehle mit `remove-iam-policy-binding`.

## C Testlauf (ein Lauf, Fristen je 15 Minuten)

```bash
gcloud workflows execute b4c-bestellcheck --location=$R --project=$P \
  --data='{"stichtag":"2026-11-09","frist_inhaber_s":900,"frist_stellvertretung_s":900}'
# nach ca. 2–3 Minuten wartet der Workflow auf die Freigabe (ohne Alarm-Mail: Anfrage so anzeigen):
python3 kleinklasse-automation/prototyp/freigeben.py --zeigen
python3 kleinklasse-automation/prototyp/freigeben.py --rolle Inhaber --freigeben \
  --menge Muesliriegel=30 --menge Cookies=40 --menge Chips=33 --menge Nuesse=42
```
Ergebnis in BigQuery (eigene Tabellen, wenige KB): `freigabe_protokoll`, `bestellmail_entwurf`.
Eskalation testen (optional): im zweiten Lauf nicht antworten → nach der ersten Frist Anfrage an die Stellvertretung, nach der zweiten «keine Freigabe» (je ein `b4c_ereignis` im Log, im Betrieb per E-Mail).

## D Zeitplan (seit SW11 angelegt)

Kein eigenes Konto für den Scheduler: Er startet den Workflow als `b4c-workflow-sa`, das dafür das Recht
«Workflows Invoker» bekommt (auf einem einzelnen Workflow lässt es sich nicht vergeben, nur auf dem Projekt).
```bash
gcloud projects add-iam-policy-binding $P --member="serviceAccount:b4c-workflow-sa@$P.iam.gserviceaccount.com" --role="roles/workflows.invoker" --condition=None
gcloud scheduler jobs create http b4c-montag --location=$R --project=$P \
  --schedule="30 7 * * 1" --time-zone="Europe/Zurich" \
  --uri="https://workflowexecutions.googleapis.com/v1/projects/$P/locations/$R/workflows/b4c-bestellcheck/executions" \
  --http-method=POST --oauth-service-account-email="b4c-workflow-sa@$P.iam.gserviceaccount.com" \
  --description="B4C Bestell-Check jeden Montag 07:30 (Daten synthetisch)"
```
Ohne Eingabe nimmt der Workflow den Stichtag 2026-11-16, weil die synthetischen Daten am 21.11. enden.
Pausieren (z. B. nach dem Semester): `gcloud scheduler jobs pause b4c-montag --location=$R --project=$P`.

## E Aufräumen (selbst ausführen, gcloud fragt jeweils nach)

Seit SW11 nicht mehr beschrieben und nur noch Altbestand aus SW10 (einzeln löschbar, bq fragt nach):
`staging_strichliste`, `staging_bestand_montag`, `staging_lieferungen`, `staging_verderb`, `staging_vorwarnungen`
(ersetzt durch `roh_*`) und `meta_lineage` (ersetzt durch `meta_bereinigung`), z. B. `bq rm -t $P:b4c_bestellcheck.meta_lineage`.

```bash
gcloud scheduler jobs delete b4c-montag --location=$R --project=$P
# Alarm (REST): Richtlinie zuerst, dann den Kanal
curl -X DELETE "https://monitoring.googleapis.com/v3/projects/$P/alertPolicies/12156258945515208134" -H "Authorization: Bearer $(gcloud auth print-access-token)" -H "x-goog-user-project: $P"
curl -X DELETE "https://monitoring.googleapis.com/v3/projects/$P/notificationChannels/17558113069386582374" -H "Authorization: Bearer $(gcloud auth print-access-token)" -H "x-goog-user-project: $P"
gcloud projects remove-iam-policy-binding $P --member="serviceAccount:b4c-workflow-sa@$P.iam.gserviceaccount.com" --role="roles/workflows.invoker"
gcloud workflows delete b4c-bestellcheck --location=$R --project=$P
gcloud run jobs delete b4c-wochenlauf --region=$R --project=$P
gcloud artifacts repositories delete cloud-run-source-deploy --location=$R --project=$P
bq rm -r -d $P:b4c_bestellcheck
gcloud storage rm --recursive gs://$P-daten
gcloud storage rm --recursive gs://run-sources-$P-$R            # von gcloud beim Build angelegt
gcloud iam service-accounts delete b4c-job-sa@$P.iam.gserviceaccount.com --project=$P
gcloud iam service-accounts delete b4c-workflow-sa@$P.iam.gserviceaccount.com --project=$P
# Alles auf einmal (inkl. Abrechnungsverknüpfung): Projekt löschen, 30 Tage wiederherstellbar
gcloud projects delete $P
```
