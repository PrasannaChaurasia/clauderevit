import { readFileSync, existsSync } from 'fs'
import { join } from 'path'

const RESULT_JSON = process.env.BRIDGE_DIR
  ? join(process.env.BRIDGE_DIR, 'result.json')
  : 'C:\\tools\\revit-bridge\\result.json'

function getModelData() {
  try {
    if (!existsSync(RESULT_JSON)) return null
    const raw = readFileSync(RESULT_JSON, 'utf8')
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export default function Dashboard() {
  const data = getModelData()

  return (
    <main style={{
      background: '#12121a',
      minHeight: '100vh',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      color: '#e8e8f0',
      padding: '32px',
    }}>
      <header style={{ marginBottom: 40 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 8 }}>
          <div style={{
            width: 10, height: 10, borderRadius: '50%',
            background: data ? '#50d27a' : '#666',
          }} />
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 600, color: '#c8a96e' }}>
            ClaudeRevit Dashboard
          </h1>
        </div>
        <p style={{ margin: 0, fontSize: 13, color: '#666' }}>
          Live model data via file bridge · Refresh to update ·{' '}
          {data ? 'Connected' : 'No data — run a command from Claude first'}
        </p>
      </header>

      {!data && (
        <div style={{
          background: '#1e1e2a', border: '1px solid #333', borderRadius: 8,
          padding: 32, textAlign: 'center', color: '#666'
        }}>
          <p style={{ fontSize: 16, marginBottom: 8 }}>No model data available yet.</p>
          <p style={{ fontSize: 13 }}>
            1. Open Revit and click <strong style={{ color: '#c8a96e' }}>Start Listener</strong><br/>
            2. Run any command from Claude Desktop or the ClaudeRevit tab<br/>
            3. Refresh this page
          </p>
        </div>
      )}

      {data && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 20 }}>
          {data.model_name && (
            <Card title="Model" accent>
              <Stat label="Name" value={data.model_name} />
              {data.status && <Stat label="Last Status" value={data.status} />}
            </Card>
          )}

          {data.levels && (
            <Card title="Levels">
              <Stat label="Count" value={data.levels.length} />
              {data.levels.slice(0, 6).map((l: { name: string; elevation_m?: number }, i: number) => (
                <div key={i} style={{ fontSize: 12, color: '#aaa', marginTop: 4 }}>
                  {l.name}{l.elevation_m !== undefined ? ` — ${l.elevation_m.toFixed(2)}m` : ''}
                </div>
              ))}
              {data.levels.length > 6 && (
                <div style={{ fontSize: 11, color: '#555', marginTop: 4 }}>
                  +{data.levels.length - 6} more
                </div>
              )}
            </Card>
          )}

          {data.walls !== undefined && (
            <Card title="Elements">
              <Stat label="Walls" value={data.walls} />
              {data.floors !== undefined && <Stat label="Floors" value={data.floors} />}
              {data.rooms !== undefined && <Stat label="Rooms" value={data.rooms} />}
              {data.sheets !== undefined && <Stat label="Sheets" value={data.sheets} />}
            </Card>
          )}

          {data.rooms_list && (
            <Card title="Rooms">
              <Stat label="Total" value={data.rooms_list.length} />
              {data.rooms_list.slice(0, 5).map((r: { name: string; number?: string; area_sqm?: number }, i: number) => (
                <div key={i} style={{ fontSize: 12, color: '#aaa', marginTop: 4 }}>
                  {r.number && <span style={{ color: '#c8a96e', marginRight: 6 }}>{r.number}</span>}
                  {r.name}{r.area_sqm ? ` (${r.area_sqm.toFixed(1)}m²)` : ''}
                </div>
              ))}
            </Card>
          )}

          {data.sheets_list && (
            <Card title="Sheets">
              <Stat label="Total" value={data.sheets_list.length} />
              {data.sheets_list.slice(0, 5).map((s: { number: string; name: string }, i: number) => (
                <div key={i} style={{ fontSize: 12, color: '#aaa', marginTop: 4 }}>
                  <span style={{ color: '#c8a96e', marginRight: 6 }}>{s.number}</span>
                  {s.name}
                </div>
              ))}
            </Card>
          )}

          {data.message && (
            <Card title="Last Response">
              <p style={{ fontSize: 13, color: '#aaa', margin: 0, lineHeight: 1.6 }}>
                {data.message}
              </p>
            </Card>
          )}
        </div>
      )}

      <footer style={{ marginTop: 48, fontSize: 11, color: '#444', textAlign: 'center' }}>
        ClaudeRevit · Urban Matrix · Refresh to pull latest model data from bridge
      </footer>
    </main>
  )
}

function Card({ title, children, accent }: {
  title: string; children: React.ReactNode; accent?: boolean
}) {
  return (
    <div style={{
      background: '#1a1a26',
      border: `1px solid ${accent ? '#c8a96e44' : '#2a2a3a'}`,
      borderRadius: 10,
      padding: '20px 22px',
    }}>
      <h3 style={{
        margin: '0 0 14px 0', fontSize: 13, fontWeight: 600,
        color: accent ? '#c8a96e' : '#8888aa', textTransform: 'uppercase', letterSpacing: 1
      }}>
        {title}
      </h3>
      {children}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
      <span style={{ fontSize: 13, color: '#666' }}>{label}</span>
      <span style={{ fontSize: 13, color: '#e8e8f0', fontWeight: 500 }}>{String(value)}</span>
    </div>
  )
}
