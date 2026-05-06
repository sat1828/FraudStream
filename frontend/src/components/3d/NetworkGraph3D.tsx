'use client'

import { useRef, useState, useMemo, useCallback, useEffect } from 'react'
import { Canvas, useFrame, ThreeEvent } from '@react-three/fiber'
import { OrbitControls, Html } from '@react-three/drei'
import * as THREE from 'three'

// ─── Types ────────────────────────────────────────────────────────────────────
interface GraphNode {
  id: string
  label: string
  type: 'normal' | 'fraud' | 'merchant' | 'review'
  txnCount: number
  totalAmount: number
  // mutable position — updated by force simulation
  x: number; y: number; z: number
  vx: number; vy: number; vz: number
}

interface GraphEdge {
  source: string
  target: string
  fraudulent: boolean
  amount: number
}

// ─── Color map ────────────────────────────────────────────────────────────────
const COLORS = {
  normal:   '#00d4ff',
  fraud:    '#ff2d55',
  merchant: '#a855f7',
  review:   '#ffb800',
}

// ─── Generate realistic graph data ───────────────────────────────────────────
function buildGraphData(): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const rand = (min: number, max: number) => Math.random() * (max - min) + min

  const nodes: GraphNode[] = []
  const edges: GraphEdge[] = []

  // 30 normal VPAs — spread loosely
  for (let i = 0; i < 30; i++) {
    nodes.push({
      id: `u${i}`, label: `user${i}@okicici`, type: 'normal',
      txnCount: Math.floor(rand(2, 20)), totalAmount: rand(1000, 80000),
      x: rand(-18, 18), y: rand(-18, 18), z: rand(-10, 10),
      vx: 0, vy: 0, vz: 0,
    })
  }

  // 8 fraud/mule VPAs — tightly clustered in one corner
  const mc = { x: 10, y: 8, z: 2 }
  for (let i = 0; i < 8; i++) {
    nodes.push({
      id: `m${i}`, label: `mule${String(i).padStart(4,'0')}@paytm`, type: 'fraud',
      txnCount: Math.floor(rand(10, 60)), totalAmount: rand(50000, 500000),
      x: mc.x + rand(-4, 4), y: mc.y + rand(-4, 4), z: mc.z + rand(-3, 3),
      vx: 0, vy: 0, vz: 0,
    })
  }

  // 8 merchants — outer ring
  for (let i = 0; i < 8; i++) {
    const angle = (i / 8) * Math.PI * 2
    nodes.push({
      id: `merch${i}`, label: `shop${i}@ybl`, type: 'merchant',
      txnCount: Math.floor(rand(20, 100)), totalAmount: rand(10000, 200000),
      x: Math.cos(angle) * 15, y: Math.sin(angle) * 15, z: rand(-5, 5),
      vx: 0, vy: 0, vz: 0,
    })
  }

  // 4 under-review
  for (let i = 0; i < 4; i++) {
    nodes.push({
      id: `rev${i}`, label: `suspect${i}@sbi`, type: 'review',
      txnCount: Math.floor(rand(5, 25)), totalAmount: rand(20000, 100000),
      x: rand(-12, 12), y: rand(-12, 12), z: rand(-8, 8),
      vx: 0, vy: 0, vz: 0,
    })
  }

  // Edges: normal → merchant (legit transactions)
  for (let i = 0; i < 60; i++) {
    const u = Math.floor(Math.random() * 30)
    const m = Math.floor(Math.random() * 8)
    edges.push({ source: `u${u}`, target: `merch${m}`, fraudulent: false, amount: rand(100, 5000) })
  }
  // Edges: normal → mule (fraud flows)
  for (let i = 0; i < 25; i++) {
    const u = Math.floor(Math.random() * 30)
    const m = Math.floor(Math.random() * 8)
    edges.push({ source: `u${u}`, target: `m${m}`, fraudulent: true, amount: rand(10000, 49999) })
  }
  // Mule ↔ mule ring
  for (let i = 0; i < 12; i++) {
    const a = Math.floor(Math.random() * 8)
    const b = (a + 1 + Math.floor(Math.random() * 7)) % 8
    edges.push({ source: `m${a}`, target: `m${b}`, fraudulent: true, amount: rand(1000, 30000) })
  }
  // Review nodes connected
  for (let i = 0; i < 8; i++) {
    const r = Math.floor(Math.random() * 4)
    const u = Math.floor(Math.random() * 30)
    edges.push({ source: `u${u}`, target: `rev${r}`, fraudulent: false, amount: rand(5000, 50000) })
  }

  return { nodes, edges }
}

// ─── Force simulation (runs in JS, updates node positions) ───────────────────
function useForceSimulation(nodes: GraphNode[], edges: GraphEdge[]) {
  const nodeMap = useMemo(() => new Map(nodes.map(n => [n.id, n])), [nodes])
  const simNodes = useRef(nodes.map(n => ({ ...n })))

  const tick = useCallback(() => {
    const ns = simNodes.current
    const REPULSION = 80
    const ATTRACTION = 0.015
    const DAMPING    = 0.85
    const FRAUD_CLUSTER = 1.5  // extra attraction between fraud nodes

    // Repulsion between all node pairs
    for (let i = 0; i < ns.length; i++) {
      for (let j = i + 1; j < ns.length; j++) {
        const dx = ns[i].x - ns[j].x
        const dy = ns[i].y - ns[j].y
        const dz = ns[i].z - ns[j].z
        const dist2 = dx * dx + dy * dy + dz * dz + 0.01
        const dist  = Math.sqrt(dist2)
        const force = REPULSION / dist2
        ns[i].vx += (dx / dist) * force
        ns[i].vy += (dy / dist) * force
        ns[i].vz += (dz / dist) * force
        ns[j].vx -= (dx / dist) * force
        ns[j].vy -= (dy / dist) * force
        ns[j].vz -= (dz / dist) * force
      }
    }

    // Spring attraction along edges
    for (const edge of edges) {
      const a = ns.find(n => n.id === edge.source)
      const b = ns.find(n => n.id === edge.target)
      if (!a || !b) continue
      const dx = b.x - a.x
      const dy = b.y - a.y
      const dz = b.z - a.z
      const dist = Math.sqrt(dx * dx + dy * dy + dz * dz) + 0.01
      const strength = ATTRACTION * (edge.fraudulent ? FRAUD_CLUSTER : 1)
      a.vx += dx * strength; a.vy += dy * strength; a.vz += dz * strength
      b.vx -= dx * strength; b.vy -= dy * strength; b.vz -= dz * strength
    }

    // Integrate + dampen
    for (const n of ns) {
      n.vx *= DAMPING; n.vy *= DAMPING; n.vz *= DAMPING
      n.x  += n.vx;   n.y  += n.vy;   n.z  += n.vz
      // Bounding sphere
      const r = Math.sqrt(n.x*n.x + n.y*n.y + n.z*n.z)
      if (r > 22) { n.x *= 22/r; n.y *= 22/r; n.z *= 22/r }
    }
  }, [edges])

  return { simNodes, tick }
}

// ─── Single node mesh ─────────────────────────────────────────────────────────
function NodeMesh({
  node, onHover
}: {
  node: GraphNode
  onHover: (n: GraphNode | null) => void
}) {
  const meshRef   = useRef<THREE.Mesh>(null)
  const lightRef  = useRef<THREE.PointLight>(null)
  const [hovered, setHovered] = useState(false)
  const baseColor = useMemo(() => new THREE.Color(COLORS[node.type]), [node.type])
  const radius    = node.type === 'merchant' ? 0.35 : node.type === 'fraud' ? 0.3 : 0.2

  useFrame(({ clock }) => {
    if (!meshRef.current) return
    const t = clock.elapsedTime

    if (node.type === 'fraud') {
      // Pulsing scale + intensity
      const pulse = 1 + 0.2 * Math.sin(t * 3.0)
      meshRef.current.scale.setScalar(hovered ? 1.8 : pulse)
      if (lightRef.current) lightRef.current.intensity = 1.5 + Math.sin(t * 3) * 0.8
    } else {
      meshRef.current.scale.setScalar(hovered ? 1.6 : 1)
    }
  })

  return (
    <group position={[node.x, node.y, node.z]}>
      <mesh
        ref={meshRef}
        onPointerEnter={(e: ThreeEvent<PointerEvent>) => { e.stopPropagation(); setHovered(true); onHover(node) }}
        onPointerLeave={() => { setHovered(false); onHover(null) }}
      >
        <sphereGeometry args={[radius, 20, 20]} />
        <meshStandardMaterial
          color={baseColor}
          emissive={baseColor}
          emissiveIntensity={node.type === 'fraud' ? 1.0 : hovered ? 0.8 : 0.3}
          roughness={0.15}
          metalness={0.7}
          transparent
          opacity={0.95}
        />
      </mesh>

      {/* Glow ring around fraud nodes */}
      {node.type === 'fraud' && (
        <>
          <mesh rotation={[Math.PI / 2, 0, 0]}>
            <ringGeometry args={[radius + 0.1, radius + 0.25, 32]} />
            <meshBasicMaterial color={COLORS.fraud} transparent opacity={0.25} side={THREE.DoubleSide} />
          </mesh>
          <pointLight ref={lightRef} color={COLORS.fraud} intensity={2} distance={5} />
        </>
      )}

      {/* Hover HTML tooltip */}
      {hovered && (
        <Html distanceFactor={18} center>
          <div style={{
            background: 'rgba(4,13,24,0.95)',
            border: `1px solid ${COLORS[node.type]}`,
            borderRadius: '8px',
            padding: '8px 12px',
            whiteSpace: 'nowrap',
            fontFamily: 'monospace',
            fontSize: '11px',
            color: '#e8f4ff',
            boxShadow: `0 0 20px ${COLORS[node.type]}40`,
            pointerEvents: 'none',
          }}>
            <div style={{ color: COLORS[node.type], fontWeight: 700, marginBottom: 4 }}>
              {node.type.toUpperCase()}
            </div>
            <div>{node.label}</div>
            <div style={{ color: '#7aa8d4', marginTop: 4 }}>
              {node.txnCount} txns · ₹{(node.totalAmount / 1000).toFixed(1)}k
            </div>
          </div>
        </Html>
      )}
    </group>
  )
}

// ─── Edge line ────────────────────────────────────────────────────────────────
function EdgeLine({ ax, ay, az, bx, by, bz, fraudulent }: {
  ax: number; ay: number; az: number
  bx: number; by: number; bz: number
  fraudulent: boolean
}) {
  const points  = useMemo(
    () => [new THREE.Vector3(ax, ay, az), new THREE.Vector3(bx, by, bz)],
    [ax, ay, az, bx, by, bz]
  )
  const geometry = useMemo(() => new THREE.BufferGeometry().setFromPoints(points), [points])

  return (
    <line geometry={geometry}>
      <lineBasicMaterial
        color={fraudulent ? '#ff2d55' : '#00d4ff'}
        opacity={fraudulent ? 0.45 : 0.1}
        transparent
        linewidth={1}
      />
    </line>
  )
}

// ─── Scene (runs force ticks per frame) ──────────────────────────────────────
function Scene() {
  const { nodes, edges } = useMemo(() => buildGraphData(), [])
  const { simNodes, tick } = useForceSimulation(nodes, edges)
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null)
  const [frame, setFrame] = useState(0)

  const bgParticlePositions = useMemo(() => {
    const pos = new Float32Array(300 * 3)
    for (let i = 0; i < 300; i++) {
      pos[i * 3]     = (Math.random() - 0.5) * 60
      pos[i * 3 + 1] = (Math.random() - 0.5) * 60
      pos[i * 3 + 2] = (Math.random() - 0.5) * 60
    }
    return pos
  }, [])

  const bgRef = useRef<THREE.Points>(null)

  // Run force simulation + re-render
  useFrame(() => {
    tick()
    setFrame(f => f + 1) // trigger re-render so nodes move
    if (bgRef.current) bgRef.current.rotation.y += 0.0003
  })

  return (
    <>
      <ambientLight intensity={0.25} />
      <directionalLight position={[15, 10, 8]} intensity={0.6} color="#00d4ff" />
      <directionalLight position={[-12, -8, -5]} intensity={0.3} color="#a855f7" />

      {/* Background star field */}
      <points ref={bgRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[bgParticlePositions, 3]} />
        </bufferGeometry>
        <pointsMaterial size={0.06} color="#00d4ff" transparent opacity={0.25} sizeAttenuation />
      </points>

      {/* Edges — redrawn every frame because nodes move */}
      {edges.map((edge, i) => {
        const a = simNodes.current.find(n => n.id === edge.source)
        const b = simNodes.current.find(n => n.id === edge.target)
        if (!a || !b) return null
        return (
          <EdgeLine key={i}
            ax={a.x} ay={a.y} az={a.z}
            bx={b.x} by={b.y} bz={b.z}
            fraudulent={edge.fraudulent}
          />
        )
      })}

      {/* Nodes */}
      {simNodes.current.map(node => (
        <NodeMesh key={node.id} node={node} onHover={setHoveredNode} />
      ))}

      <OrbitControls
        enablePan
        enableZoom
        autoRotate
        autoRotateSpeed={0.4}
        minDistance={8}
        maxDistance={50}
      />
    </>
  )
}

// ─── Public export ────────────────────────────────────────────────────────────
export default function NetworkGraph3D() {
  return (
    <Canvas
      camera={{ position: [0, 0, 32], fov: 58 }}
      style={{ background: 'transparent', width: '100%', height: '100%' }}
      gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
      dpr={[1, 1.5]}          // cap at 1.5x for performance
      frameloop="always"
    >
      <Scene />
    </Canvas>
  )
}
