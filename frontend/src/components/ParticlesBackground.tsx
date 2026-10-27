import { useMemo } from 'react'
import Particles, { ParticlesProvider } from '@tsparticles/react'
import type { Engine, ISourceOptions } from '@tsparticles/engine'
import { loadSlim } from '@tsparticles/slim'

async function initEngine(engine: Engine): Promise<void> {
  await loadSlim(engine)
}

function getParticleColors(): string[] {
    const styles = getComputedStyle(document.documentElement)

    const colors = [
        styles.getPropertyValue('--color-particle-1').trim(),
        styles.getPropertyValue('--color-particle-2').trim(),
        styles.getPropertyValue('--color-particle-3').trim(),
        styles.getPropertyValue('--color-particle-4').trim(),
    ]

    console.log('Cores lidas do CSS:', colors)

    return colors
}

function ParticlesBackground() {
  const options = useMemo<ISourceOptions>(
    () => ({
      fullScreen: { enable: true, zIndex: 0 },
      background: { color: { value: '#0b0f1a' } },
      fpsLimit: 240,
      detectRetina: true,
      particles: {
        number: { value: 200, density: { enable: true }},
        // Na v4, a cor fica em `paint` (o antigo `particles.color` é ignorado
        // sem erro e o engine usa o padrão #fff).
        paint: {
          color: { value: getParticleColors() },
          fill: { enable: true },
        },
        shape: { type: 'square' },
        opacity: { value: { min: 0.4, max: 0.8 } },
        size: { value: { min: 1, max: 5 } },
        links: { enable: false },
        move: {
          enable: true,
          speed: 2,
          direction: 'none',
          random: true,
          straight: false,
          outModes: { default: 'out' },
        },
      },
      interactivity: {
        // O conteúdo da página fica por cima do canvas, então os eventos
        // precisam ser capturados na janela para o repulse continuar funcionando.
        detectsOn: 'window',
        events: {
          onHover: { enable: true, mode: 'repulse' },
          onClick: { enable: false },
        },
        modes: {
          repulse: { distance: 150, duration: 0.4, speed:0.07 },
        },
      },
    }),
    [],
  )

  return (
    <ParticlesProvider init={initEngine}>
      <Particles id="tsparticles" options={options} />
    </ParticlesProvider>
  )
}

export default ParticlesBackground
