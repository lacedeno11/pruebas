"""
RBAC/ABAC Guardrails Implementation

This module implements Role-Based Access Control (RBAC) and Attribute-Based Access Control (ABAC)
guardrails for the Policy Validation Copilot system as part of UC-OP-10.
"""

from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field
from datetime import datetime, time
import logging
import re

from .base import (
    BaseGuardrail, GuardrailResult, GuardrailContext, GuardrailDecision,
    GuardrailSeverity, GuardrailFlag
)

logger = logging.getLogger(__name__)


class Permission(BaseModel):
    """Permission definition"""
    name: str = Field(..., description="Permission name")
    resource_type: str = Field(..., description="Resource type this permission applies to")
    actions: List[str] = Field(..., description="Allowed actions")
    conditions: Dict[str, Any] = Field(default_factory=dict, description="Additional conditions")


class Role(BaseModel):
    """Role definition with permissions"""
    name: str = Field(..., description="Role name")
    permissions: List[Permission] = Field(..., description="Role permissions")
    inherits_from: List[str] = Field(default_factory=list, description="Parent roles")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Role attributes")


class AccessPolicy(BaseModel):
    """ABAC access policy"""
    policy_id: str = Field(..., description="Policy identifier")
    name: str = Field(..., description="Policy name")
    effect: str = Field(..., description="ALLOW or DENY")
    subjects: Dict[str, Any] = Field(..., description="Subject conditions")
    resources: Dict[str, Any] = Field(..., description="Resource conditions")
    actions: List[str] = Field(..., description="Applicable actions")
    conditions: Dict[str, Any] = Field(default_factory=dict, description="Additional conditions")
    priority: int = Field(default=100, description="Policy priority (lower = higher priority)")


class RBACGuardrail(BaseGuardrail):
    """
    Role-Based Access Control guardrail implementation.
    
    Enforces access control based on user roles and permissions.
    """
    
    def __init__(self):
        super().__init__("RBAC", "1.0.0")
        self.roles: Dict[str, Role] = {}
        self.role_hierarchy: Dict[str, Set[str]] = {}
        self._initialize_default_roles()
    
    def _initialize_default_roles(self):
        """Initialize default roles and permissions"""
        # Case Reviewer role
        case_reviewer_permissions = [
            Permission(
                name="case.read",
                resource_type="case",
                actions=["read", "view"],
                conditions={"assigned_to_user": True}
            ),
            Permission(
                name="case.update_status",
                resource_type="case",
                actions=["update_status"],
                conditions={"status_transitions": ["PENDIENTE", "EN_REVISION"]}
            ),
            Permission(
                name="evidence.read",
                resource_type="evidence",
                actions=["read", "view"]
            )
        ]
        
        # Senior Reviewer role
        senior_reviewer_permissions = [
            Permission(
                name="case.full_access",
                resource_type="case",
                actions=["read", "update", "approve", "reject"]
            ),
            Permission(
                name="evidence.full_access",
                resource_type="evidence",
                actions=["read", "create", "update"]
            ),
            Permission(
                name="policy.read",
                resource_type="policy",
                actions=["read", "view"]
            )
        ]
        
        # Administrator role
        admin_permissions = [
            Permission(
                name="system.admin",
                resource_type="*",
                actions=["*"]
            )
        ]
        
        # System role (for automated processes)
        system_permissions = [
            Permission(
                name="case.system_process",
                resource_type="case",
                actions=["create", "read", "update", "process"]
            ),
            Permission(
                name="ml.invoke",
                resource_type="ml_service",
                actions=["invoke", "predict"]
            )
        ]
        
        # Register roles
        self.register_role(Role(
            name="case_reviewer",
            permissions=case_reviewer_permissions
        ))
        
        self.register_role(Role(
            name="senior_reviewer",
            permissions=senior_reviewer_permissions,
            inherits_from=["case_reviewer"]
        ))
        
        self.register_role(Role(
            name="administrator",
            permissions=admin_permissions,
            inherits_from=["senior_reviewer"]
        ))
        
        self.register_role(Role(
            name="system",
            permissions=system_permissions
        ))
    
    def register_role(self, role: Role) -> None:
        """Register a role with the RBAC system"""
        self.roles[role.name] = role
        
        # Build role hierarchy
        if role.name not in self.role_hierarchy:
            self.role_hierarchy[role.name] = set()
        
        for parent_role in role.inherits_from:
            if parent_role in self.role_hierarchy:
                self.role_hierarchy[role.name].update(self.role_hierarchy[parent_role])
            self.role_hierarchy[role.name].add(parent_role)
        
        logger.info(f"Registered RBAC role: {role.name}")
    
    def get_effective_permissions(self, user_roles: List[str]) -> List[Permission]:
        """Get all effective permissions for user roles"""
        all_permissions = []
        processed_roles = set()
        
        def collect_permissions(role_name: str):
            if role_name in processed_roles or role_name not in self.roles:
                return
            
            processed_roles.add(role_name)
            role = self.roles[role_name]
            
            # Add role's own permissions
            all_permissions.extend(role.permissions)
            
            # Add inherited permissions
            for parent_role in role.inherits_from:
                collect_permissions(parent_role)
        
        # Collect permissions from all user roles
        for role_name in user_roles:
            collect_permissions(role_name)
        
        return all_permissions
    
    def check_permission(
        self, 
        user_roles: List[str], 
        resource_type: str, 
        action: str,
        context: Dict[str, Any] = None
    ) -> bool:
        """Check if user has permission for action on resource"""
        permissions = self.get_effective_permissions(user_roles)
        context = context or {}
        
        for permission in permissions:
            # Check resource type match
            if permission.resource_type != "*" and permission.resource_type != resource_type:
                continue
            
            # Check action match
            if "*" not in permission.actions and action not in permission.actions:
                continue
            
            # Check conditions
            if self._check_permission_conditions(permission, context):
                return True
        
        return False
    
    def _check_permission_conditions(self, permission: Permission, context: Dict[str, Any]) -> bool:
        """Check if permission conditions are met"""
        for condition_key, condition_value in permission.conditions.items():
            if condition_key == "assigned_to_user":
                if condition_value and context.get("assigned_user_id") != context.get("user_id"):
                    return False
            elif condition_key == "status_transitions":
                current_status = context.get("current_status")
                if current_status and current_status not in condition_value:
                    return False
            elif condition_key == "time_restriction":
                if not self._check_time_restriction(condition_value):
                    return False
        
        return True
    
    def _check_time_restriction(self, time_restriction: Dict[str, Any]) -> bool:
        """Check time-based access restrictions"""
        now = datetime.now()
        
        # Check business hours
        if "business_hours" in time_restriction:
            start_time = time.fromisoformat(time_restriction["business_hours"]["start"])
            end_time = time.fromisoformat(time_restriction["business_hours"]["end"])
            current_time = now.time()
            
            if not (start_time <= current_time <= end_time):
                return False
        
        # Check allowed days
        if "allowed_days" in time_restriction:
            allowed_days = time_restriction["allowed_days"]  # 0=Monday, 6=Sunday
            if now.weekday() not in allowed_days:
                return False
        
        return True
    
    async def evaluate(self, payload: Dict[str, Any], context: GuardrailContext) -> GuardrailResult:
        """Evaluate RBAC permissions"""
        flags = []
        decision = GuardrailDecision.ALLOW
        
        # Check if user has required roles
        if not context.user_roles:
            flags.append(await self._create_flag(
                flag_type="RBAC_NO_ROLES",
                severity=GuardrailSeverity.HIGH,
                message="User has no assigned roles",
                rule_id="RBAC-001"
            ))
            decision = GuardrailDecision.BLOCK
        
        # Check permission for the requested action
        elif not self.check_permission(
            context.user_roles,
            context.resource_type,
            context.action,
            {
                "user_id": context.user_id,
                "assigned_user_id": payload.get("assigned_user_id"),
                "current_status": payload.get("status")
            }
        ):
            flags.append(await self._create_flag(
                flag_type="RBAC_ACCESS_DENIED",
                severity=GuardrailSeverity.HIGH,
                message=f"User lacks permission for {context.action} on {context.resource_type}",
                details={
                    "user_roles": context.user_roles,
                    "required_action": context.action,
                    "resource_type": context.resource_type
                },
                rule_id="RBAC-002"
            ))
            decision = GuardrailDecision.BLOCK
        
        # Log access attempt
        await self._log_security_event(
            event_type="RBAC_ACCESS_CHECK",
            severity=GuardrailSeverity.LOW if decision == GuardrailDecision.ALLOW else GuardrailSeverity.HIGH,
            description=f"RBAC check for {context.action} on {context.resource_type}",
            context=context,
            flags=flags
        )
        
        return GuardrailResult(
            decision=decision,
            flags=flags,
            security_context={
                "rbac_check": True,
                "effective_permissions": [p.name for p in self.get_effective_permissions(context.user_roles)]
            },
            guardrail_version=self.version
        )
    
    def get_rule_ids(self) -> List[str]:
        """Get RBAC rule IDs"""
        return ["RBAC-001", "RBAC-002", "RBAC-003"]


class ABACGuardrail(BaseGuardrail):
    """
    Attribute-Based Access Control guardrail implementation.
    
    Enforces fine-grained access control based on attributes of users,
    resources, actions, and environment.
    """
    
    def __init__(self):
        super().__init__("ABAC", "1.0.0")
        self.policies: List[AccessPolicy] = []
        self._initialize_default_policies()
    
    def _initialize_default_policies(self):
        """Initialize default ABAC policies"""
        # High-value case policy
        high_value_policy = AccessPolicy(
            policy_id="ABAC-001",
            name="High Value Case Restriction",
            effect="DENY",
            subjects={"roles": ["case_reviewer"]},
            resources={"case_amount": {"$gt": 10000}},
            actions=["approve"],
            conditions={
                "require_senior_approval": True
            },
            priority=10
        )
        
        # Sensitive data access policy
        sensitive_data_policy = AccessPolicy(
            policy_id="ABAC-002",
            name="Sensitive Data Access",
            effect="ALLOW",
            subjects={"clearance_level": {"$gte": 3}},
            resources={"data_classification": "SENSITIVE"},
            actions=["read", "view"],
            conditions={
                "time_restriction": {
                    "business_hours": {"start": "08:00", "end": "18:00"}
                }
            },
            priority=20
        )
        
        # Emergency override policy
        emergency_policy = AccessPolicy(
            policy_id="ABAC-003",
            name="Emergency Override",
            effect="ALLOW",
            subjects={"roles": ["administrator"]},
            resources={"*": "*"},
            actions=["*"],
            conditions={
                "emergency_mode": True,
                "audit_required": True
            },
            priority=1
        )
        
        self.policies.extend([high_value_policy, sensitive_data_policy, emergency_policy])
    
    def add_policy(self, policy: AccessPolicy) -> None:
        """Add an ABAC policy"""
        self.policies.append(policy)
        # Sort by priority (lower number = higher priority)
        self.policies.sort(key=lambda p: p.priority)
        logger.info(f"Added ABAC policy: {policy.name}")
    
    def evaluate_policies(
        self, 
        subject_attributes: Dict[str, Any],
        resource_attributes: Dict[str, Any],
        action: str,
        environment_attributes: Dict[str, Any] = None
    ) -> Tuple[bool, List[str]]:
        """Evaluate ABAC policies for access decision"""
        environment_attributes = environment_attributes or {}
        applied_policies = []
        
        # Default deny
        access_granted = False
        
        for policy in self.policies:
            if self._policy_matches(
                policy, subject_attributes, resource_attributes, action, environment_attributes
            ):
                applied_policies.append(policy.policy_id)
                
                if policy.effect == "ALLOW":
                    access_granted = True
                elif policy.effect == "DENY":
                    access_granted = False
                    break  # DENY takes precedence
        
        return access_granted, applied_policies
    
    def _policy_matches(
        self,
        policy: AccessPolicy,
        subject_attrs: Dict[str, Any],
        resource_attrs: Dict[str, Any],
        action: str,
        env_attrs: Dict[str, Any]
    ) -> bool:
        """Check if policy matches current request"""
        # Check action
        if "*" not in policy.actions and action not in policy.actions:
            return False
        
        # Check subject conditions
        if not self._check_attribute_conditions(policy.subjects, subject_attrs):
            return False
        
        # Check resource conditions
        if not self._check_attribute_conditions(policy.resources, resource_attrs):
            return False
        
        # Check environment conditions
        if not self._check_attribute_conditions(policy.conditions, env_attrs):
            return False
        
        return True
    
    def _check_attribute_conditions(
        self, 
        conditions: Dict[str, Any], 
        attributes: Dict[str, Any]
    ) -> bool:
        """Check if attribute conditions are satisfied"""
        for condition_key, condition_value in conditions.items():
            if condition_key not in attributes:
                return False
            
            attr_value = attributes[condition_key]
            
            # Handle different condition types
            if isinstance(condition_value, dict):
                # MongoDB-style operators
                for operator, operand in condition_value.items():
                    if operator == "$gt" and not (attr_value > operand):
                        return False
                    elif operator == "$gte" and not (attr_value >= operand):
                        return False
                    elif operator == "$lt" and not (attr_value < operand):
                        return False
                    elif operator == "$lte" and not (attr_value <= operand):
                        return False
                    elif operator == "$eq" and not (attr_value == operand):
                        return False
                    elif operator == "$ne" and not (attr_value != operand):
                        return False
                    elif operator == "$in" and attr_value not in operand:
                        return False
                    elif operator == "$nin" and attr_value in operand:
                        return False
            elif isinstance(condition_value, list):
                # Check if attribute value is in list
                if attr_value not in condition_value:
                    return False
            else:
                # Direct equality check
                if attr_value != condition_value:
                    return False
        
        return True
    
    async def evaluate(self, payload: Dict[str, Any], context: GuardrailContext) -> GuardrailResult:
        """Evaluate ABAC policies"""
        flags = []
        decision = GuardrailDecision.ALLOW
        
        # Prepare attributes
        subject_attributes = {
            "user_id": context.user_id,
            "roles": context.user_roles,
            "permissions": context.user_permissions,
            "clearance_level": payload.get("user_clearance_level", 1)
        }
        
        resource_attributes = {
            "resource_type": context.resource_type,
            "resource_id": context.resource_id,
            "case_amount": payload.get("service_amount", 0),
            "data_classification": payload.get("data_classification", "PUBLIC"),
            "sensitivity_level": payload.get("sensitivity_level", 1)
        }
        
        environment_attributes = {
            "time": context.timestamp,
            "source_ip": context.source_ip,
            "emergency_mode": payload.get("emergency_mode", False),
            "business_hours": self._is_business_hours(context.timestamp)
        }
        
        # Evaluate policies
        access_granted, applied_policies = self.evaluate_policies(
            subject_attributes,
            resource_attributes,
            context.action,
            environment_attributes
        )
        
        if not access_granted:
            flags.append(await self._create_flag(
                flag_type="ABAC_ACCESS_DENIED",
                severity=GuardrailSeverity.HIGH,
                message=f"ABAC policies deny {context.action} on {context.resource_type}",
                details={
                    "applied_policies": applied_policies,
                    "subject_attributes": subject_attributes,
                    "resource_attributes": resource_attributes
                },
                rule_id="ABAC-001"
            ))
            decision = GuardrailDecision.BLOCK
        
        # Check for high-risk conditions
        if payload.get("service_amount", 0) > 50000:
            flags.append(await self._create_flag(
                flag_type="ABAC_HIGH_VALUE",
                severity=GuardrailSeverity.MEDIUM,
                message="High-value transaction requires additional oversight",
                details={"amount": payload.get("service_amount")},
                rule_id="ABAC-002"
            ))
            if decision == GuardrailDecision.ALLOW:
                decision = GuardrailDecision.REQUIRE_HITL
        
        # Log access decision
        await self._log_security_event(
            event_type="ABAC_ACCESS_CHECK",
            severity=GuardrailSeverity.LOW if access_granted else GuardrailSeverity.HIGH,
            description=f"ABAC evaluation for {context.action} on {context.resource_type}",
            context=context,
            flags=flags,
            metadata={
                "applied_policies": applied_policies,
                "access_granted": access_granted
            }
        )
        
        return GuardrailResult(
            decision=decision,
            flags=flags,
            security_context={
                "abac_check": True,
                "applied_policies": applied_policies,
                "access_granted": access_granted
            },
            guardrail_version=self.version
        )
    
    def _is_business_hours(self, timestamp: datetime) -> bool:
        """Check if timestamp is within business hours"""
        # Business hours: 8 AM to 6 PM, Monday to Friday
        if timestamp.weekday() >= 5:  # Weekend
            return False
        
        business_start = time(8, 0)
        business_end = time(18, 0)
        current_time = timestamp.time()
        
        return business_start <= current_time <= business_end
    
    def get_rule_ids(self) -> List[str]:
        """Get ABAC rule IDs"""
        return ["ABAC-001", "ABAC-002", "ABAC-003"]
