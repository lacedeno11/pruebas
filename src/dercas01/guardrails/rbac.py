"""
Role-Based Access Control (RBAC) for DERCAS 01 Policy Validation Copilot

Implements comprehensive RBAC and authorization system with fine-grained permissions,
role hierarchies, and context-aware access control.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum

from pydantic import BaseModel, Field

from ..models.enums import UserRole

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """System permissions."""
    
    # Case management
    CASE_CREATE = "case:create"
    CASE_READ = "case:read"
    CASE_UPDATE = "case:update"
    CASE_DELETE = "case:delete"
    CASE_ASSIGN = "case:assign"
    CASE_CLOSE = "case:close"
    
    # Policy management
    POLICY_CREATE = "policy:create"
    POLICY_READ = "policy:read"
    POLICY_UPDATE = "policy:update"
    POLICY_DELETE = "policy:delete"
    POLICY_APPROVE = "policy:approve"
    POLICY_PUBLISH = "policy:publish"
    
    # Exception management
    EXCEPTION_CREATE = "exception:create"
    EXCEPTION_READ = "exception:read"
    EXCEPTION_UPDATE = "exception:update"
    EXCEPTION_DELETE = "exception:delete"
    EXCEPTION_APPROVE = "exception:approve"
    
    # Decision making
    DECISION_READ = "decision:read"
    DECISION_OVERRIDE = "decision:override"
    DECISION_APPROVE = "decision:approve"
    DECISION_REJECT = "decision:reject"
    
    # HITL operations
    HITL_REVIEW = "hitl:review"
    HITL_ASSIGN = "hitl:assign"
    HITL_ESCALATE = "hitl:escalate"
    HITL_APPROVE = "hitl:approve"
    
    # Audit and reporting
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"
    AUDIT_DELETE = "audit:delete"
    
    # System administration
    SYSTEM_CONFIG = "system:config"
    SYSTEM_MONITOR = "system:monitor"
    SYSTEM_BACKUP = "system:backup"
    SYSTEM_RESTORE = "system:restore"
    
    # User management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_ASSIGN_ROLE = "user:assign_role"
    
    # ML and analytics
    ML_TRAIN = "ml:train"
    ML_DEPLOY = "ml:deploy"
    ML_MONITOR = "ml:monitor"
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_EXPORT = "analytics:export"


class AccessContext(BaseModel):
    """Context for access control decisions."""
    
    # User information
    user_id: str
    user_roles: List[UserRole]
    user_groups: List[str] = Field(default_factory=list)
    
    # Request context
    resource_type: str
    resource_id: Optional[str] = None
    action: str
    
    # Environmental context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Business context
    insurer_id: Optional[str] = None
    case_priority: Optional[str] = None
    case_status: Optional[str] = None
    data_sensitivity: Optional[str] = None
    
    # Session context
    session_id: Optional[str] = None
    authentication_method: Optional[str] = None
    mfa_verified: bool = False


class AccessDecision(BaseModel):
    """Result of an access control decision."""
    
    granted: bool
    reason: str
    conditions: List[str] = Field(default_factory=list)
    
    # Decision metadata
    decision_time: datetime = Field(default_factory=datetime.utcnow)
    decision_basis: List[str] = Field(default_factory=list)
    required_permissions: List[Permission] = Field(default_factory=list)
    
    # Audit information
    policy_version: Optional[str] = None
    rule_applied: Optional[str] = None
    
    # Additional restrictions
    time_limited: bool = False
    expires_at: Optional[datetime] = None
    requires_approval: bool = False
    requires_mfa: bool = False


class RoleDefinition(BaseModel):
    """Definition of a role with permissions and constraints."""
    
    role: UserRole
    permissions: Set[Permission]
    inherits_from: List[UserRole] = Field(default_factory=list)
    
    # Constraints
    max_session_duration: Optional[timedelta] = None
    allowed_ip_ranges: List[str] = Field(default_factory=list)
    allowed_hours: Optional[Tuple[int, int]] = None  # (start_hour, end_hour)
    requires_mfa: bool = False
    
    # Business constraints
    allowed_insurers: List[str] = Field(default_factory=list)
    max_case_value: Optional[float] = None
    allowed_case_statuses: List[str] = Field(default_factory=list)


class AccessPolicy(BaseModel):
    """Access control policy rule."""
    
    policy_id: str
    name: str
    description: str
    
    # Conditions
    roles: List[UserRole] = Field(default_factory=list)
    permissions: List[Permission] = Field(default_factory=list)
    resources: List[str] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)
    
    # Context conditions
    time_conditions: Optional[Dict[str, Any]] = None
    location_conditions: Optional[Dict[str, Any]] = None
    business_conditions: Optional[Dict[str, Any]] = None
    
    # Decision
    effect: str = "ALLOW"  # ALLOW or DENY
    priority: int = 0
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    active: bool = True


class RBACService:
    """
    Role-Based Access Control service.
    
    Provides comprehensive authorization and access control with:
    - Role-based permissions
    - Context-aware decisions
    - Policy-based access control
    - Audit logging
    """
    
    def __init__(self):
        self.role_definitions = self._initialize_role_definitions()
        self.access_policies = self._initialize_access_policies()
        self.access_cache: Dict[str, AccessDecision] = {}
        self.cache_ttl = timedelta(minutes=5)
    
    def _initialize_role_definitions(self) -> Dict[UserRole, RoleDefinition]:
        """Initialize default role definitions."""
        roles = {}
        
        # Agent role
        roles[UserRole.AGENT] = RoleDefinition(
            role=UserRole.AGENT,
            permissions={
                Permission.CASE_READ,
                Permission.CASE_UPDATE,
                Permission.CASE_ASSIGN,
                Permission.DECISION_READ,
                Permission.HITL_REVIEW,
                Permission.AUDIT_READ,
                Permission.POLICY_READ,
                Permission.EXCEPTION_READ,
            },
            max_session_duration=timedelta(hours=8),
            requires_mfa=False,
            allowed_hours=(6, 22),  # 6 AM to 10 PM
        )
        
        # Supervisor role
        roles[UserRole.SUPERVISOR] = RoleDefinition(
            role=UserRole.SUPERVISOR,
            permissions={
                Permission.CASE_READ,
                Permission.CASE_UPDATE,
                Permission.CASE_ASSIGN,
                Permission.CASE_CLOSE,
                Permission.DECISION_READ,
                Permission.DECISION_OVERRIDE,
                Permission.DECISION_APPROVE,
                Permission.HITL_REVIEW,
                Permission.HITL_ASSIGN,
                Permission.HITL_ESCALATE,
                Permission.AUDIT_READ,
                Permission.AUDIT_EXPORT,
                Permission.POLICY_READ,
                Permission.EXCEPTION_READ,
                Permission.EXCEPTION_APPROVE,
                Permission.ANALYTICS_READ,
            },
            inherits_from=[UserRole.AGENT],
            max_session_duration=timedelta(hours=12),
            requires_mfa=True,
            max_case_value=100000.0,
        )
        
        # Auditor role
        roles[UserRole.AUDITOR] = RoleDefinition(
            role=UserRole.AUDITOR,
            permissions={
                Permission.CASE_READ,
                Permission.DECISION_READ,
                Permission.AUDIT_READ,
                Permission.AUDIT_EXPORT,
                Permission.POLICY_READ,
                Permission.EXCEPTION_READ,
                Permission.ANALYTICS_READ,
                Permission.ANALYTICS_EXPORT,
            },
            max_session_duration=timedelta(hours=8),
            requires_mfa=True,
        )
        
        # Admin role
        roles[UserRole.ADMIN] = RoleDefinition(
            role=UserRole.ADMIN,
            permissions=set(Permission),  # All permissions
            max_session_duration=timedelta(hours=4),
            requires_mfa=True,
        )
        
        # System role (for automated processes)
        roles[UserRole.SYSTEM] = RoleDefinition(
            role=UserRole.SYSTEM,
            permissions={
                Permission.CASE_CREATE,
                Permission.CASE_READ,
                Permission.CASE_UPDATE,
                Permission.DECISION_READ,
                Permission.AUDIT_READ,
                Permission.ML_TRAIN,
                Permission.ML_DEPLOY,
                Permission.ML_MONITOR,
                Permission.SYSTEM_MONITOR,
            },
            requires_mfa=False,
        )
        
        return roles
    
    def _initialize_access_policies(self) -> List[AccessPolicy]:
        """Initialize default access policies."""
        policies = []
        
        # High-value case policy
        policies.append(AccessPolicy(
            policy_id="high_value_case_policy",
            name="High Value Case Access",
            description="Restrict access to high-value cases",
            resources=["case"],
            actions=["read", "update", "approve"],
            business_conditions={
                "case_value": {"operator": "gt", "value": 50000}
            },
            effect="DENY",
            priority=100,
            created_by="system"
        ))
        
        # Sensitive data policy
        policies.append(AccessPolicy(
            policy_id="sensitive_data_policy",
            name="Sensitive Data Access",
            description="Require MFA for sensitive data access",
            resources=["audit", "policy"],
            actions=["export", "delete"],
            effect="ALLOW",
            priority=50,
            created_by="system"
        ))
        
        # Time-based access policy
        policies.append(AccessPolicy(
            policy_id="business_hours_policy",
            name="Business Hours Access",
            description="Restrict certain operations to business hours",
            actions=["approve", "delete", "export"],
            time_conditions={
                "allowed_hours": [6, 22],
                "allowed_days": [1, 2, 3, 4, 5]  # Monday to Friday
            },
            effect="DENY",
            priority=75,
            created_by="system"
        ))
        
        return policies
    
    def check_access(self, context: AccessContext) -> AccessDecision:
        """
        Check if access should be granted based on context.
        
        Args:
            context: Access context with user, resource, and environmental information
            
        Returns:
            AccessDecision with grant/deny and reasoning
        """
        try:
            # Check cache first
            cache_key = self._generate_cache_key(context)
            if cache_key in self.access_cache:
                cached_decision = self.access_cache[cache_key]
                if datetime.utcnow() - cached_decision.decision_time < self.cache_ttl:
                    return cached_decision
            
            # Perform access check
            decision = self._evaluate_access(context)
            
            # Cache the decision
            self.access_cache[cache_key] = decision
            
            # Log the decision
            self._log_access_decision(context, decision)
            
            return decision
            
        except Exception as e:
            logger.error(f"Access check failed: {e}")
            return AccessDecision(
                granted=False,
                reason=f"Access check error: {str(e)}",
                decision_basis=["error"]
            )
    
    def _evaluate_access(self, context: AccessContext) -> AccessDecision:
        """Evaluate access based on roles, permissions, and policies."""
        decision_basis = []
        conditions = []
        required_permissions = []
        
        # Step 1: Check if user has any valid roles
        if not context.user_roles:
            return AccessDecision(
                granted=False,
                reason="No roles assigned to user",
                decision_basis=["no_roles"]
            )
        
        # Step 2: Determine required permissions for the action
        required_perms = self._get_required_permissions(context.resource_type, context.action)
        required_permissions.extend(required_perms)
        
        if not required_perms:
            return AccessDecision(
                granted=False,
                reason=f"No permissions defined for {context.resource_type}:{context.action}",
                decision_basis=["undefined_permissions"]
            )
        
        # Step 3: Check if user has required permissions through roles
        user_permissions = self._get_user_permissions(context.user_roles)
        missing_permissions = required_perms - user_permissions
        
        if missing_permissions:
            return AccessDecision(
                granted=False,
                reason=f"Missing permissions: {[p.value for p in missing_permissions]}",
                decision_basis=["insufficient_permissions"],
                required_permissions=list(required_perms)
            )
        
        decision_basis.append("permissions_granted")
        
        # Step 4: Check role constraints
        constraint_check = self._check_role_constraints(context)
        if not constraint_check[0]:
            return AccessDecision(
                granted=False,
                reason=constraint_check[1],
                decision_basis=["role_constraints"]
            )
        
        decision_basis.append("role_constraints_passed")
        
        # Step 5: Evaluate access policies
        policy_decision = self._evaluate_policies(context)
        if not policy_decision.granted:
            return policy_decision
        
        decision_basis.extend(policy_decision.decision_basis)
        conditions.extend(policy_decision.conditions)
        
        # Step 6: Check for additional security requirements
        security_requirements = self._check_security_requirements(context)
        conditions.extend(security_requirements)
        
        return AccessDecision(
            granted=True,
            reason="Access granted based on role permissions and policies",
            conditions=conditions,
            decision_basis=decision_basis,
            required_permissions=list(required_perms)
        )
    
    def _get_required_permissions(self, resource_type: str, action: str) -> Set[Permission]:
        """Get required permissions for a resource and action."""
        permission_map = {
            ("case", "create"): {Permission.CASE_CREATE},
            ("case", "read"): {Permission.CASE_READ},
            ("case", "update"): {Permission.CASE_UPDATE},
            ("case", "delete"): {Permission.CASE_DELETE},
            ("case", "assign"): {Permission.CASE_ASSIGN},
            ("case", "close"): {Permission.CASE_CLOSE},
            
            ("policy", "create"): {Permission.POLICY_CREATE},
            ("policy", "read"): {Permission.POLICY_READ},
            ("policy", "update"): {Permission.POLICY_UPDATE},
            ("policy", "delete"): {Permission.POLICY_DELETE},
            ("policy", "approve"): {Permission.POLICY_APPROVE},
            ("policy", "publish"): {Permission.POLICY_PUBLISH},
            
            ("exception", "create"): {Permission.EXCEPTION_CREATE},
            ("exception", "read"): {Permission.EXCEPTION_READ},
            ("exception", "update"): {Permission.EXCEPTION_UPDATE},
            ("exception", "delete"): {Permission.EXCEPTION_DELETE},
            ("exception", "approve"): {Permission.EXCEPTION_APPROVE},
            
            ("decision", "read"): {Permission.DECISION_READ},
            ("decision", "override"): {Permission.DECISION_OVERRIDE},
            ("decision", "approve"): {Permission.DECISION_APPROVE},
            ("decision", "reject"): {Permission.DECISION_REJECT},
            
            ("hitl", "review"): {Permission.HITL_REVIEW},
            ("hitl", "assign"): {Permission.HITL_ASSIGN},
            ("hitl", "escalate"): {Permission.HITL_ESCALATE},
            ("hitl", "approve"): {Permission.HITL_APPROVE},
            
            ("audit", "read"): {Permission.AUDIT_READ},
            ("audit", "export"): {Permission.AUDIT_EXPORT},
            ("audit", "delete"): {Permission.AUDIT_DELETE},
            
            ("system", "config"): {Permission.SYSTEM_CONFIG},
            ("system", "monitor"): {Permission.SYSTEM_MONITOR},
            ("system", "backup"): {Permission.SYSTEM_BACKUP},
            ("system", "restore"): {Permission.SYSTEM_RESTORE},
            
            ("user", "create"): {Permission.USER_CREATE},
            ("user", "read"): {Permission.USER_READ},
            ("user", "update"): {Permission.USER_UPDATE},
            ("user", "delete"): {Permission.USER_DELETE},
            ("user", "assign_role"): {Permission.USER_ASSIGN_ROLE},
            
            ("ml", "train"): {Permission.ML_TRAIN},
            ("ml", "deploy"): {Permission.ML_DEPLOY},
            ("ml", "monitor"): {Permission.ML_MONITOR},
            
            ("analytics", "read"): {Permission.ANALYTICS_READ},
            ("analytics", "export"): {Permission.ANALYTICS_EXPORT},
        }
        
        return permission_map.get((resource_type, action), set())
    
    def _get_user_permissions(self, user_roles: List[UserRole]) -> Set[Permission]:
        """Get all permissions for user roles including inherited permissions."""
        all_permissions = set()
        
        for role in user_roles:
            if role in self.role_definitions:
                role_def = self.role_definitions[role]
                all_permissions.update(role_def.permissions)
                
                # Add inherited permissions
                for inherited_role in role_def.inherits_from:
                    if inherited_role in self.role_definitions:
                        inherited_permissions = self._get_user_permissions([inherited_role])
                        all_permissions.update(inherited_permissions)
        
        return all_permissions
    
    def _check_role_constraints(self, context: AccessContext) -> Tuple[bool, str]:
        """Check role-specific constraints."""
        for role in context.user_roles:
            if role not in self.role_definitions:
                continue
            
            role_def = self.role_definitions[role]
            
            # Check time constraints
            if role_def.allowed_hours:
                current_hour = context.timestamp.hour
                start_hour, end_hour = role_def.allowed_hours
                if not (start_hour <= current_hour <= end_hour):
                    return False, f"Access not allowed outside business hours for role {role.value}"
            
            # Check IP constraints
            if role_def.allowed_ip_ranges and context.ip_address:
                # Simplified IP check - in production would use proper CIDR matching
                ip_allowed = any(
                    context.ip_address.startswith(ip_range.split('/')[0][:8])
                    for ip_range in role_def.allowed_ip_ranges
                )
                if not ip_allowed:
                    return False, f"IP address not allowed for role {role.value}"
            
            # Check MFA requirement
            if role_def.requires_mfa and not context.mfa_verified:
                return False, f"MFA required for role {role.value}"
            
            # Check business constraints
            if role_def.allowed_insurers and context.insurer_id:
                if context.insurer_id not in role_def.allowed_insurers:
                    return False, f"Insurer access not allowed for role {role.value}"
        
        return True, "Role constraints satisfied"
    
    def _evaluate_policies(self, context: AccessContext) -> AccessDecision:
        """Evaluate access policies."""
        applicable_policies = []
        
        # Find applicable policies
        for policy in self.access_policies:
            if not policy.active:
                continue
            
            if self._policy_applies(policy, context):
                applicable_policies.append(policy)
        
        # Sort by priority (higher priority first)
        applicable_policies.sort(key=lambda p: p.priority, reverse=True)
        
        # Evaluate policies in priority order
        for policy in applicable_policies:
            if policy.effect == "DENY":
                return AccessDecision(
                    granted=False,
                    reason=f"Access denied by policy: {policy.name}",
                    decision_basis=[f"policy_deny_{policy.policy_id}"],
                    policy_version=policy.policy_id,
                    rule_applied=policy.name
                )
        
        # If no DENY policies matched, check for ALLOW policies
        allow_policies = [p for p in applicable_policies if p.effect == "ALLOW"]
        if allow_policies:
            return AccessDecision(
                granted=True,
                reason=f"Access allowed by policy: {allow_policies[0].name}",
                decision_basis=[f"policy_allow_{allow_policies[0].policy_id}"],
                policy_version=allow_policies[0].policy_id,
                rule_applied=allow_policies[0].name
            )
        
        # Default allow if no policies apply
        return AccessDecision(
            granted=True,
            reason="No applicable policies, default allow",
            decision_basis=["default_allow"]
        )
    
    def _policy_applies(self, policy: AccessPolicy, context: AccessContext) -> bool:
        """Check if a policy applies to the given context."""
        # Check roles
        if policy.roles and not any(role in context.user_roles for role in policy.roles):
            return False
        
        # Check resources
        if policy.resources and context.resource_type not in policy.resources:
            return False
        
        # Check actions
        if policy.actions and context.action not in policy.actions:
            return False
        
        # Check time conditions
        if policy.time_conditions:
            if not self._check_time_conditions(policy.time_conditions, context):
                return False
        
        # Check business conditions
        if policy.business_conditions:
            if not self._check_business_conditions(policy.business_conditions, context):
                return False
        
        return True
    
    def _check_time_conditions(self, time_conditions: Dict[str, Any], context: AccessContext) -> bool:
        """Check time-based conditions."""
        current_time = context.timestamp
        
        # Check allowed hours
        if "allowed_hours" in time_conditions:
            allowed_hours = time_conditions["allowed_hours"]
            if len(allowed_hours) == 2:
                start_hour, end_hour = allowed_hours
                if not (start_hour <= current_time.hour <= end_hour):
                    return False
        
        # Check allowed days
        if "allowed_days" in time_conditions:
            allowed_days = time_conditions["allowed_days"]
            if current_time.weekday() + 1 not in allowed_days:  # weekday() returns 0-6
                return False
        
        return True
    
    def _check_business_conditions(self, business_conditions: Dict[str, Any], context: AccessContext) -> bool:
        """Check business-specific conditions."""
        # Check case value conditions
        if "case_value" in business_conditions:
            case_value_condition = business_conditions["case_value"]
            operator = case_value_condition.get("operator")
            threshold = case_value_condition.get("value")
            
            # Would need to fetch actual case value from context or database
            # For now, using a placeholder
            actual_value = getattr(context, "case_value", 0)
            
            if operator == "gt" and actual_value <= threshold:
                return False
            elif operator == "lt" and actual_value >= threshold:
                return False
            elif operator == "eq" and actual_value != threshold:
                return False
        
        return True
    
    def _check_security_requirements(self, context: AccessContext) -> List[str]:
        """Check for additional security requirements."""
        conditions = []
        
        # Check for sensitive operations
        sensitive_actions = ["delete", "export", "approve", "override"]
        if context.action in sensitive_actions:
            conditions.append("audit_required")
            
            if not context.mfa_verified:
                conditions.append("mfa_recommended")
        
        # Check for high-value operations
        if context.case_priority == "CRITICAL":
            conditions.append("supervisor_notification_required")
        
        return conditions
    
    def _generate_cache_key(self, context: AccessContext) -> str:
        """Generate cache key for access decision."""
        key_parts = [
            context.user_id,
            ",".join(role.value for role in context.user_roles),
            context.resource_type,
            context.resource_id or "",
            context.action,
            str(context.mfa_verified),
        ]
        return "|".join(key_parts)
    
    def _log_access_decision(self, context: AccessContext, decision: AccessDecision):
        """Log access control decision for audit purposes."""
        log_data = {
            "user_id": context.user_id,
            "user_roles": [role.value for role in context.user_roles],
            "resource_type": context.resource_type,
            "resource_id": context.resource_id,
            "action": context.action,
            "granted": decision.granted,
            "reason": decision.reason,
            "conditions": decision.conditions,
            "ip_address": context.ip_address,
            "timestamp": context.timestamp.isoformat(),
        }
        
        if decision.granted:
            logger.info(f"Access granted: {log_data}")
        else:
            logger.warning(f"Access denied: {log_data}")
    
    def get_user_permissions(self, user_roles: List[UserRole]) -> List[Permission]:
        """Get all permissions for a user."""
        permissions = self._get_user_permissions(user_roles)
        return list(permissions)
    
    def add_role_definition(self, role_def: RoleDefinition):
        """Add or update a role definition."""
        self.role_definitions[role_def.role] = role_def
        logger.info(f"Role definition updated: {role_def.role.value}")
    
    def add_access_policy(self, policy: AccessPolicy):
        """Add an access policy."""
        self.access_policies.append(policy)
        logger.info(f"Access policy added: {policy.policy_id}")
    
    def remove_access_policy(self, policy_id: str) -> bool:
        """Remove an access policy."""
        for i, policy in enumerate(self.access_policies):
            if policy.policy_id == policy_id:
                del self.access_policies[i]
                logger.info(f"Access policy removed: {policy_id}")
                return True
        return False
    
    def clear_cache(self):
        """Clear the access decision cache."""
        self.access_cache.clear()
        logger.info("Access decision cache cleared")


# Factory function
def create_rbac_service() -> RBACService:
    """Create an RBAC service with default configuration."""
    return RBACService()


# Utility functions
def check_permission(user_roles: List[UserRole], required_permission: Permission, rbac_service: RBACService) -> bool:
    """Quick permission check for a user."""
    user_permissions = rbac_service._get_user_permissions(user_roles)
    return required_permission in user_permissions


def create_access_context(
    user_id: str,
    user_roles: List[UserRole],
    resource_type: str,
    action: str,
    resource_id: Optional[str] = None,
    **kwargs
) -> AccessContext:
    """Create an access context for authorization checks."""
    return AccessContext(
        user_id=user_id,
        user_roles=user_roles,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        **kwargs
    )


def require_permission(permission: Permission):
    """Decorator to require a specific permission for a function."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # This would be implemented with proper context extraction
            # For now, it's a placeholder
            logger.info(f"Permission check required: {permission.value}")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(role: UserRole):
    """Decorator to require a specific role for a function."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # This would be implemented with proper context extraction
            # For now, it's a placeholder
            logger.info(f"Role check required: {role.value}")
            return func(*args, **kwargs)
        return wrapper
    return decorator
