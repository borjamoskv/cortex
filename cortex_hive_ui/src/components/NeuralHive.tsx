import { useRef, useMemo, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Stars, Text } from '@react-three/drei';
import { Bloom, EffectComposer } from '@react-three/postprocessing';
import * as THREE from 'three';
import type { Node, Link } from '../api/client';

// Cyber-palette based on MEJORAlo aesthetics
const COLORS: Record<string, string> = {
  knowledge: '#00dcb4', // Teal (Axioms)
  ghost: '#7d5fff',    // Purple (Ontology)
  error: '#ff5f56',    // Red
  workflow: '#ffbe0b', // Yellow
  default: '#ffffff',
  glow: '#00dcb4'
};

// --- HELPER: Deterministic Node Positioning ---
const getNodePosition = (node: Node): THREE.Vector3 => {
    // Better dispersion using Fibonacci Sphere or similar deterministic hash
    const id = node.id || 0;
    const phi = Math.acos(-1 + (2 * (id % 100)) / 100);
    const theta = Math.sqrt(Math.PI * 100) * phi;
    const r = 18 + (node.val || 1) * 1.5; 
    
    return new THREE.Vector3(
      r * Math.cos(theta) * Math.sin(phi),
      r * Math.sin(theta) * Math.sin(phi),
      r * Math.cos(phi)
    );
};

const NodeMesh = ({ node, onClick }: { node: Node; onClick: (node: Node) => void }) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const [hovered, setHover] = useState(false);

  useFrame((state) => {
    if (meshRef.current) {
       const t = state.clock.getElapsedTime();
       meshRef.current.position.y += Math.sin(t * 1.5 + node.id) * 0.005;
       if (hovered) {
           meshRef.current.scale.setScalar(1.2 + Math.sin(t * 4) * 0.1);
       } else {
           meshRef.current.scale.lerp(new THREE.Vector3(1, 1, 1), 0.1);
       }
    }
  });

  const pos = useMemo(() => getNodePosition(node), [node]);
  const color = COLORS[node.group] || COLORS.default;

  return (
    <group position={pos}>
      <mesh
        ref={meshRef}
        onClick={(e) => { e.stopPropagation(); onClick(node); }}
        onPointerOver={() => setHover(true)}
        onPointerOut={() => setHover(false)}
      >
        <sphereGeometry args={[node.val ? node.val / 2 : 0.6, 32, 32]} />
        <meshStandardMaterial
          color={hovered ? '#ffffff' : color}
          emissive={color}
          emissiveIntensity={hovered ? 5 : 2}
          roughness={0}
          metalness={1}
        />
      </mesh>
      
      {(hovered || node.val > 2) && (
        <Text
          position={[0, (node.val || 1) + 1.5, 0]}
          fontSize={hovered ? 1.2 : 0.8}
          color="#ffffff"
          anchorX="center"
          anchorY="middle"
        >
          {node.name}
        </Text>
      )}
      
      {/* Halo for high-relevance nodes */}
      {node.val > 3 && (
        <mesh rotation={[Math.PI / 2, 0, 0]}>
            <ringGeometry args={[node.val, node.val + 0.1, 64]} />
            <meshBasicMaterial color={color} transparent opacity={0.3} side={THREE.DoubleSide} />
        </mesh>
      )}
    </group>
  );
};

const Synapses = ({ links, nodes }: { links: Link[], nodes: Node[] }) => {
    const nodeMap = useMemo(() => {
        const map = new Map<number, Node>();
        nodes.forEach(n => map.set(n.id, n));
        return map;
    }, [nodes]);

    const linePoints = useMemo(() => {
        const points: THREE.Vector3[] = [];
        links.forEach(link => {
            const source = nodeMap.get(link.source);
            const target = nodeMap.get(link.target);
            if (source && target) {
                points.push(getNodePosition(source), getNodePosition(target));
            }
        });
        return points;
    }, [links, nodeMap]);

    return (
        <group>
            {/* Using a single BufferGeometry for all lines for performance */}
            <lineSegments>
                <bufferGeometry>
                    <float32BufferAttribute 
                        attach="attributes-position" 
                        args={[new Float32Array(linePoints.flatMap(p => p.toArray())), 3]} 
                    />
                </bufferGeometry>
                <lineBasicMaterial color="#00dcb4" transparent opacity={0.1} />
            </lineSegments>
        </group>
    )
}

export const NeuralHiveGraph = ({ nodes, links, onNodeClick }: { nodes: Node[], links: Link[], onNodeClick: (n: Node) => void }) => {
  return (
    <group>
      {nodes.map(node => (
        <NodeMesh key={node.id} node={node} onClick={onNodeClick} />
      ))}
      <Synapses links={links} nodes={nodes} />
    </group>
  );
};

export default function NeuralHive({ data, onNodeSelect }: { data: { nodes: Node[], links: Link[] }, onNodeSelect: (n: Node) => void }) {
  return (
    <div className="w-full h-full relative">
      <Canvas camera={{ position: [0, 0, 50], fov: 60 }} dpr={[1, 2]}>
        <color attach="background" args={['#020202']} />
        
        <ambientLight intensity={0.5} />
        <pointLight position={[10, 10, 10]} intensity={2} color="#00dcb4" />
        <pointLight position={[-10, -10, -10]} intensity={2} color="#7d5fff" />
        
        <Stars radius={100} depth={50} count={7000} factor={4} saturation={0} fade speed={1} />
        
        <EffectComposer>
            <Bloom 
                intensity={1.5} 
                luminanceThreshold={0.2} 
                luminanceSmoothing={0.9} 
                mipmapBlur 
            />
            <NeuralHiveGraph nodes={data.nodes} links={data.links} onNodeClick={onNodeSelect} />
        </EffectComposer>
        
        <OrbitControls 
            autoRotate 
            autoRotateSpeed={0.3} 
            enablePan={false}
            minDistance={15}
            maxDistance={80}
            makeDefault
        />
      </Canvas>
      
      {/* Legend & Stats Overlay */}
      <div className="absolute top-40 right-8 flex flex-col gap-2 pointer-events-none">
          {Object.entries(COLORS).filter(([k]) => k !== 'glow' && k !== 'default').map(([name, color]) => (
              <div key={name} className="legend-item" style={{ '--legend-color': color } as React.CSSProperties}>
                  <span className="legend-label">{name}</span>
                  <div className="legend-indicator" />
              </div>
          ))}
      </div>

      <div className="absolute bottom-8 left-8 pointer-events-none font-mono">
          <div className="flex items-center gap-2 mb-1">
              <div className="w-2 h-2 bg-[#00dcb4] animate-ping rounded-full" />
              <h3 className="text-[#00dcb4] text-xs uppercase tracking-widest font-bold">Neural Core Online</h3>
          </div>
          <p className="text-white/20 text-[10px]">Processing {data.nodes.length} Axioms and {data.links.length} Synapses</p>
      </div>
    </div>
  );
}
