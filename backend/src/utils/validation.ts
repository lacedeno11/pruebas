import { z } from 'zod';

export const OTStatusEnum = z.enum([
  'PREPLANIFICADA',
  'PLANIFICADA',
  'ASIGNADO_TAREA',
  'DETENIDA',
  'ANULADA',
  'FINALIZADA',
]);

export const ProjectTypeEnum = z.enum(['PUBLICO', 'PRIVADO', 'TERCERIZADO']);

export const CreateOTSchema = z.object({
  externalId: z.string().min(1),
  status: OTStatusEnum.default('PREPLANIFICADA'),
  projectType: ProjectTypeEnum,
  lat: z.number().optional(),
  long: z.number().optional(),
  clienteName: z.string().optional(),
  loginId: z.string().optional(),
});

export const UpdateOTStatusSchema = z.object({
  status: OTStatusEnum,
  reason: z.string().optional(),
});

export const AssignCuadrillaSchema = z.object({
  otId: z.string().uuid(),
  cuadrillaId: z.string().uuid(),
  force: z.boolean().default(false),
});

export type CreateOTInput = z.infer<typeof CreateOTSchema>;
export type UpdateOTStatusInput = z.infer<typeof UpdateOTStatusSchema>;
export type AssignCuadrillaInput = z.infer<typeof AssignCuadrillaSchema>;
export type OTStatus = z.infer<typeof OTStatusEnum>;
export type ProjectType = z.infer<typeof ProjectTypeEnum>;

