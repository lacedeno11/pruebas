import { PrismaClient, OTStatus, ProjectType, CuadrillaType } from '@prisma/client';
import { faker } from '@faker-js/faker';

const prisma = new PrismaClient();

// Ecuador city coordinates
const ECUADOR_CITIES = [
  { name: 'Quito', lat: -0.2198, long: -78.5096 },
  { name: 'Guayaquil', lat: -2.1894, long: -79.8623 },
  { name: 'Cuenca', lat: -2.9001, long: -78.9994 },
];

// Generate random coordinates within Ecuador bounds
function generateEcuadorCoordinates(): { lat: number; long: number } {
  const city = ECUADOR_CITIES[Math.floor(Math.random() * ECUADOR_CITIES.length)];
  const latOffset = (Math.random() - 0.5) * 0.3; // ±0.15 degrees
  const longOffset = (Math.random() - 0.5) * 0.3; // ±0.15 degrees

  return {
    lat: city.lat + latOffset,
    long: city.long + longOffset,
  };
}

// Generate cuadrilla names
function generateCuadrillaName(type: CuadrillaType, index: number): string {
  const regions = ['Norte', 'Sur', 'Este', 'Oeste', 'Centro'];
  const region = regions[index % regions.length];

  if (type === 'PRINCIPAL') {
    return `Cuadrilla ${region} ${Math.floor(index / 5) + 1}`;
  } else {
    return `Cuadrilla ${region} Reserva`;
  }
}

async function main() {
  try {
    console.log('🌱 Starting database seed...');

    // Use transaction for atomicity
    await prisma.$transaction(async (tx) => {
      // Clear existing data
      console.log('🗑️  Clearing existing data...');
      await tx.assignment.deleteMany();
      await tx.agentLog.deleteMany();
      await tx.oT.deleteMany();
      await tx.cuadrilla.deleteMany();

      // Create 10 cuadrillas (5 PRINCIPAL, 5 RESERVA)
      console.log('👷 Creating 10 cuadrillas...');
      const cuadrillas = await Promise.all([
        // Principal crews
        ...Array.from({ length: 5 }).map((_, i) =>
          tx.cuadrilla.create({
            data: {
              name: generateCuadrillaName('PRINCIPAL', i),
              type: 'PRINCIPAL' as CuadrillaType,
              dailyCapacity: 10,
              currentLoad: 0,
              isActive: true,
              lastCentroidLat: generateEcuadorCoordinates().lat,
              lastCentroidLong: generateEcuadorCoordinates().long,
            },
          })
        ),
        // Reserve crews
        ...Array.from({ length: 5 }).map((_, i) =>
          tx.cuadrilla.create({
            data: {
              name: generateCuadrillaName('RESERVA', i),
              type: 'RESERVA' as CuadrillaType,
              dailyCapacity: 10,
              currentLoad: 0,
              isActive: true,
              lastCentroidLat: generateEcuadorCoordinates().lat,
              lastCentroidLong: generateEcuadorCoordinates().long,
            },
          })
        ),
      ]);

      console.log(`✅ Created ${cuadrillas.length} cuadrillas`);

      // Create 50 OTs with distributed statuses
      console.log('📋 Creating 50 OTs...');
      const statuses: OTStatus[] = [];
      const projectTypes: ProjectType[] = [];

      // Distribute statuses: 20 PREPLANIFICADA, 15 PLANIFICADA, 10 ASIGNADO_TAREA, 3 DETENIDA, 2 ANULADA
      statuses.push(
        ...Array(20).fill('PREPLANIFICADA' as OTStatus),
        ...Array(15).fill('PLANIFICADA' as OTStatus),
        ...Array(10).fill('ASIGNADO_TAREA' as OTStatus),
        ...Array(3).fill('DETENIDA' as OTStatus),
        ...Array(2).fill('ANULADA' as OTStatus)
      );

      // Distribute project types: 30% PUBLICO, 50% PRIVADO, 20% TERCERIZADO
      for (let i = 0; i < 50; i++) {
        const rand = Math.random();
        if (rand < 0.3) {
          projectTypes.push('PUBLICO' as ProjectType);
        } else if (rand < 0.8) {
          projectTypes.push('PRIVADO' as ProjectType);
        } else {
          projectTypes.push('TERCERIZADO' as ProjectType);
        }
      }

      // Shuffle arrays to randomize distribution
      const shuffleArray = <T,>(array: T[]): T[] => {
        const shuffled = [...array];
        for (let i = shuffled.length - 1; i > 0; i--) {
          const j = Math.floor(Math.random() * (i + 1));
          [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
        }
        return shuffled;
      };

      const shuffledStatuses = shuffleArray(statuses);
      const shuffledProjectTypes = shuffleArray(projectTypes);

      const ots = await Promise.all(
        Array.from({ length: 50 }).map((_, i) => {
          const coords = generateEcuadorCoordinates();
          return tx.oT.create({
            data: {
              externalId: `EXT-OT-${Date.now()}-${i}`,
              status: shuffledStatuses[i],
              projectType: shuffledProjectTypes[i],
              clienteName: faker.company.name(),
              loginId: `LOGIN-${i + 1}`,
              lat: coords.lat,
              long: coords.long,
              hasGeoError: false,
            },
          });
        })
      );

      console.log(`✅ Created ${ots.length} OTs`);

      // Assign 30 random OTs to cuadrillas
      console.log('🔗 Creating 30 assignments...');
      const otIndices = Array.from({ length: 50 }, (_, i) => i);
      const assignedIndices = otIndices
        .sort(() => Math.random() - 0.5)
        .slice(0, 30);

      const assignments = await Promise.all(
        assignedIndices.map((otIndex) => {
          const ot = ots[otIndex];
          const cuadrilla = cuadrillas[Math.floor(Math.random() * cuadrillas.length)];

          return tx.assignment.create({
            data: {
              otId: ot.id,
              cuadrillaId: cuadrilla.id,
              assignedByAgent: 'Seed Script',
              distanceFromCentroid: Math.random() * 15, // 0-15km
            },
          });
        })
      );

      // Update OTs with assignment references and cuadrilla load
      for (const assignment of assignments) {
        const ot = ots.find((o) => o.id === assignment.otId)!;
        await tx.oT.update({
          where: { id: ot.id },
          data: { assignedCuadrillaId: assignment.cuadrillaId },
        });

        // Update cuadrilla currentLoad
        const cuadrillaLoad = assignments.filter(
          (a) => a.cuadrillaId === assignment.cuadrillaId
        ).length;
        await tx.cuadrilla.update({
          where: { id: assignment.cuadrillaId },
          data: { currentLoad: cuadrillaLoad },
        });
      }

      console.log(`✅ Created ${assignments.length} assignments`);

      // Create 10 sample AgentLog entries
      console.log('📝 Creating 10 sample AgentLog entries...');
      const agentLogs = await Promise.all(
        Array.from({ length: 10 }).map((_, i) => {
          const randomOT = ots[Math.floor(Math.random() * ots.length)];
          const agents = [
            'OTSAgent',
            'PlanningAgent',
            'GovernanceAgent',
            'CommunicationAgent',
            'RouterAgent',
          ];
          const agent = agents[i % agents.length];

          const acciones: { [key: string]: string[] } = {
            OTSAgent: [
              'OT_INGESTION',
              'COORDINATE_VALIDATION',
              'DATABASE_REGISTRATION',
            ],
            PlanningAgent: [
              'PHASE1_BALANCE',
              'PHASE2_PROXIMITY',
              'PHASE3_OPTIMIZATION',
            ],
            GovernanceAgent: [
              'INACTIVITY_CHECK',
              'STATUS_ALERT',
              'AUTO_CANCELLATION',
            ],
            CommunicationAgent: ['SEND_NOTIFICATION', 'EMAIL_SENT', 'ALERT_POSTED'],
            RouterAgent: ['MESSAGE_ROUTING', 'INTENT_CLASSIFICATION', 'AGENT_DISPATCH'],
          };

          const actionList = acciones[agent];
          const accion = actionList[Math.floor(Math.random() * actionList.length)];

          return tx.agentLog.create({
            data: {
              otId: Math.random() > 0.2 ? randomOT.id : null,
              agentName: agent,
              accion,
              resultado: `Successfully executed ${accion}`,
              rawLlmResponse: `{"intent": "${accion.toLowerCase()}", "confidence": ${(0.7 + Math.random() * 0.3).toFixed(2)}}`,
              errorMessage: Math.random() > 0.9 ? 'Sample error for testing' : null,
            },
          });
        })
      );

      console.log(`✅ Created ${agentLogs.length} AgentLog entries`);

      console.log('\n✨ Seed completed successfully!');
      console.log(`📊 Summary:`);
      console.log(`   - Cuadrillas: ${cuadrillas.length}`);
      console.log(`   - OTs: ${ots.length}`);
      console.log(`   - Assignments: ${assignments.length}`);
      console.log(`   - AgentLogs: ${agentLogs.length}`);
    });
  } catch (error) {
    console.error('❌ Seed failed:', error);
    throw error;
  } finally {
    await prisma.$disconnect();
  }
}

main();

