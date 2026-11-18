import ParticlesBackground from './components/ParticlesBackground'
import Header from './components/Header'
import PipelineCard from './components/cards/PipelineCard'
import HistoryCard from './components/cards/HistoryCard'
import PullsCard from './components/cards/PullsCard'
import CommitsCard from './components/cards/CommitsCard'
import VersionCard from './components/cards/VersionCard'
import TeamCard from './components/cards/TeamCard'
import BranchMapCard from './components/cards/BranchMapCard'
import { useVersionReload } from './hooks/useVersionReload'
import './index.css'
import './App.css'

// Painel: cabeçalho + grade 3×2 com os 6 cards (ocupa a tela) e, rolando
// para baixo, o mapa de branches na largura toda.
//   │ 1. Status da main │ 3. PRs abertos │ 5. Versão      │
//   │ 2. Últimos runs   │ 6. Commits     │ 4. Integrantes │
//   │ 7. Mapa de branches (largura toda)                  │
function App() {
  const { offline } = useVersionReload()

  return (
    <>
      <ParticlesBackground />
      {offline && <div className="offline-banner">Reconectando…</div>}
      <main className="app">
        <Header />
        <div className="grid">
          <PipelineCard />
          <HistoryCard />
          <PullsCard />
          <CommitsCard />
          <VersionCard />
          <TeamCard />
          <BranchMapCard />
        </div>
      </main>
    </>
  )
}

export default App