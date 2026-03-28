## Neo4j AuraDB Setup

Use AuraDB as the live entity graph for Cyphron. Keep training offline.

### 1. Create the AuraDB instance

- Sign in to Neo4j Aura and create an `AuraDB Free` instance.
- Save these three values from the connection panel:
  - `URI`
  - `Username`
  - `Password`

### 2. Put the values in `.env`

Update [`.env.example`](/home/sharonprabhu/backup/devs_house_26/Cyphron/cyphron/.env.example) into your local `.env` with:

```env
NEO4J_URI=neo4j+s://<your-instance-id>.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=<your-password>
```

For Aura, prefer the `neo4j+s://` URI shown by Aura instead of `bolt://`.

### 3. Install backend dependencies

From `cyphron/pipeline`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Start the backend once

From `cyphron/pipeline`:

```bash
python main.py
```

On startup the backend now:

- creates uniqueness constraints for `Account`, `Device`, `IPAddress`, and `Phone`
- checks connectivity with `RETURN 1`

If Aura is reachable, you should see `Neo4j client initialized and reachable`.

### 5. Graph schema used by Cyphron

Nodes:

- `Account {account_id}`
- `Device {device_id}`
- `IPAddress {address}`
- `Phone {number}`

Relationships:

- `(:Account)-[:TRANSFERRED_TO {txn_id, amount, channel, currency, timestamp, merchant}]->(:Account)`
- `(:Account)-[:USES_DEVICE]->(:Device)`
- `(:Account)-[:USES_IP]->(:IPAddress)`
- `(:Account)-[:USES_PHONE]->(:Phone)`

### 6. What to write into Neo4j for each transaction

For each event, send at minimum:

- `id`
- `user_id` or `source_account_id`
- `destination_account_id` or fallback destination
- `amount`
- `channel`
- `created_at`

Optional but highly useful:

- `device_id`
- `ip_address`
- `phone_number`
- `currency`
- `merchant`

### 7. Fraud queries now available

The repo includes Cypher for:

- fan-out in a recent time window
- structuring just below threshold
- shared-device links across accounts
- 3-hop layering chains

These live in [queries.py](/home/sharonprabhu/backup/devs_house_26/Cyphron/cyphron/pipeline/graph/queries.py).

### 8. Recommended next step

Before any ML work, populate Aura with a scripted mule-ring scenario and verify:

- one hub account fans out to many recipients
- at least two accounts share a device or IP
- the fan-out query returns the hub account
- the structuring query returns near-threshold accounts when expected
