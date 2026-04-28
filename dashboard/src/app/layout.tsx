export const metadata = { title: 'ClaudeRevit Dashboard', description: 'Live Revit model data' }
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body style={{ margin: 0 }}>{children}</body></html>
}
