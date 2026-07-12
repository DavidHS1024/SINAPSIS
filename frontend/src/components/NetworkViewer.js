"use client";

import React, { useMemo } from 'react';
import { ReactFlow, Controls, Background, MarkerType } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

export default function NetworkViewer({ uceData }) {
  // Construir nodos y edges dinámicamente desde uceData
  const { nodes, edges } = useMemo(() => {
    const defaultNodes = [];
    const defaultEdges = [];

    // Nodo central: La UCE actual
    defaultNodes.push({
      id: 'center',
      position: { x: 400, y: 250 },
      data: { 
        label: (
          <div className="flex flex-col items-center justify-center p-2">
            <span className="font-bold text-acento text-lg">{uceData?.lema || 'Desconocido'}</span>
            <span className="text-xs text-niebla/70 mt-1">{uceData?.pos_mcr || '?'} | Acepc. {uceData?.numero_acepcion || 1}</span>
          </div>
        )
      },
      style: {
        background: '#0F2847', // marino-800
        color: '#E8EEF5',      // niebla
        border: '2px solid #C6A45C', // acento
        borderRadius: '8px',
        width: 180,
      }
    });

    const rels = uceData?.relaciones || {};
    
    // Si no hay relaciones, ponemos un par de mock nodes para la demo
    if (Object.keys(rels).length === 0) {
      defaultNodes.push({
        id: 'mock_hyper',
        position: { x: 400, y: 50 },
        data: { label: 'Hiperónimo (Simulado)' },
        style: { background: '#173456', color: '#E8EEF5', border: '1px solid #1F4470', borderRadius: '4px' }
      });
      defaultEdges.push({
        id: 'e-center-hyper',
        source: 'center',
        target: 'mock_hyper',
        label: 'is_a',
        animated: true,
        style: { stroke: '#C6A45C' },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#C6A45C' }
      });

      defaultNodes.push({
        id: 'mock_syn',
        position: { x: 150, y: 250 },
        data: { label: 'Sinónimo (Simulado)' },
        style: { background: '#173456', color: '#E8EEF5', border: '1px solid #1F4470', borderRadius: '4px' }
      });
      defaultEdges.push({
        id: 'e-center-syn',
        source: 'center',
        target: 'mock_syn',
        label: 'synonym',
        style: { stroke: '#1F4470', strokeDasharray: '5 5' }
      });
    } else {
      // Si hay relaciones reales, las iteraríamos aquí (Lógica futura de Combinación)
      let yOffset = 50;
      Object.entries(rels).forEach(([tipoRel, targets], idx) => {
        // ... (Para cuando combinador esté listo)
      });
    }

    return { nodes: defaultNodes, edges: defaultEdges };
  }, [uceData]);

  return (
    <div style={{ width: '100%', height: '500px' }} className="bg-[#0A1F3C] rounded border border-marino-700">
      <ReactFlow 
        nodes={nodes} 
        edges={edges}
        fitView
      >
        <Background color="#1F4470" gap={16} />
        <Controls className="bg-marino-700 fill-niebla" />
      </ReactFlow>
    </div>
  );
}
