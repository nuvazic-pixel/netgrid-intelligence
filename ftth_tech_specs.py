"""
ftth_tech_specs.py — Technical Knowledge Base for FTTH Planning
Based on Deutsche Telekom KP18440 Documentation (August 2022)

This module contains real technical parameters for FTTH network planning
as specified by Deutsche Telekom Technik GmbH.
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


# ============================================================
# GPON TECHNICAL SPECIFICATIONS
# ============================================================

class GPONSpecs:
    """GPON (Gigabit Passive Optical Network) technical parameters."""
    
    # Bitrates
    DOWNSTREAM_GBPS = 2.4  # DS: 2.488,32 Mbit/s
    UPSTREAM_GBPS = 1.2    # US: 1.244,16 Mbit/s
    
    # Wavelengths (nm)
    WAVELENGTH_UPSTREAM = 1310     # λ1 = 1310nm
    WAVELENGTH_DOWNSTREAM = 1490   # λ2 = 1490nm
    WAVELENGTH_TV = 1550           # λ3 = 1550nm (TV signal)
    WAVELENGTH_MEASUREMENT = 1625  # λ4 = 1625nm (OTDR)
    
    # Distance limits
    MAX_DISTANCE_KM = 20           # Maximum technical range
    PLANNING_DISTANCE_KM = 11      # Planning range (conservative)
    
    # Attenuation budget
    MAX_ATTENUATION_DB = 28        # Maximum optical attenuation
    MIN_ATTENUATION_DB = 13        # Minimum optical attenuation
    
    # Splitting
    MAX_SPLITTING_FACTOR = 32      # Standard PON: 1:32
    DEFAULT_SPLITTING = 32
    
    @classmethod
    def get_bitrate_per_user(cls, splitting_factor: int = 32) -> dict:
        """Calculate mean bitrate per ONT based on splitting factor."""
        return {
            "downstream_mbps": round((cls.DOWNSTREAM_GBPS * 1000) / splitting_factor, 1),
            "upstream_mbps": round((cls.UPSTREAM_GBPS * 1000) / splitting_factor, 1),
        }


# ============================================================
# SPLITTER/COUPLER SPECIFICATIONS
# ============================================================

@dataclass
class SplitterSpec:
    """Optical splitter (Koppler) specifications."""
    ratio: str
    attenuation_db: float
    use_case: str


SPLITTER_SPECS = {
    "1:4": SplitterSpec("1:4", 7.1, "Small buildings, cascaded networks"),
    "1:8": SplitterSpec("1:8", 10.5, "Medium buildings, first cascade level"),
    "1:32": SplitterSpec("1:32", 17.1, "Standard PON, central splitter"),
}


# Building size to fiber/splitter mapping (Telekom standard)
BUILDING_FIBER_CONFIG = {
    # WE (Wohneinheiten) per building → fibers, splitter config
    "1-3": {"fibers": 1, "splitter_gebaeude": None, "splitter_nvt": "1:32"},
    "4-8": {"fibers": 4, "splitter_gebaeude": "1:4", "splitter_nvt": "1:8"},
    "9-20": {"fibers": 8, "splitter_gebaeude": "1:4", "splitter_nvt": None},
    "21+": {"fibers": 12, "splitter_gebaeude": "1:32", "splitter_nvt": None},
}


# ============================================================
# CABLE SPECIFICATIONS
# ============================================================

class CableType(Enum):
    """Cable types in Telekom network."""
    MICROCABLE = "gf_mikrokabel"      # ~2.6mm outer diameter
    MINICABLE = "gf_minikabel"
    OUTDOOR_CABLE = "gf_aussenkabel"   # A-DQ(BN)H type, metal-free
    AERIAL_CABLE = "gf_luftkabel"      # Up to 72 fibers


@dataclass
class MicrocableSpec:
    """SpeedNet microcable specifications."""
    fiber_count: int
    outer_diameter_mm: float = 2.6
    tube_type: str = "SNR7"
    

MICROCABLE_VARIANTS = [
    MicrocableSpec(4),
    MicrocableSpec(6),
    MicrocableSpec(12),
    MicrocableSpec(24),
    MicrocableSpec(36),
]


# ============================================================
# MICRODUCT SPECIFICATIONS
# ============================================================

@dataclass
class MicroductSpec:
    """SpeedNet microduct (SNRV) specifications."""
    config: str  # e.g., "2x7", "12x7", "22x7"
    tube_count: int
    installation: str  # "einziehen" (pull-in) or "erdverlegt" (direct burial)


MICRODUCT_VARIANTS = [
    MicroductSpec("2x7", 2, "einziehen"),
    MicroductSpec("7x7", 7, "einziehen"),
    MicroductSpec("12x7", 12, "einziehen"),
    MicroductSpec("22x7", 22, "erdverlegt"),
]


# ============================================================
# NETWORK ARCHITECTURE
# ============================================================

class NetworkLevel(Enum):
    """Network hierarchy levels."""
    LEVEL_3 = "netzebene_3"  # GPON-OLT → Gf-AP (fiber infrastructure)
    LEVEL_4 = "netzebene_4"  # Gf-AP → ONT (building network)


@dataclass
class NetworkNodeSpec:
    """Network node specifications."""
    node_type: str
    description: str
    typical_capacity: Optional[int] = None


NETWORK_NODES = {
    "OLT": NetworkNodeSpec("OLT", "Optical Line Terminal - central office", 32),
    "Gf-HVt": NetworkNodeSpec("Gf-HVt", "Glasfaser-Hauptverteiler - main distribution"),
    "Gf-NVt": NetworkNodeSpec("Gf-NVt", "Glasfaser-Netzverteiler - network distributor", 32),
    "Gf-AP": NetworkNodeSpec("Gf-AP", "Glasfaser-Abschlusspunkt - building termination"),
    "ONT": NetworkNodeSpec("ONT", "Optical Network Terminal - customer premises"),
}


# ============================================================
# COPPER CABLE SPECIFICATIONS (Legacy/Hybrid)
# ============================================================

@dataclass
class CopperCableSpec:
    """Copper cable wire gauge specifications."""
    diameter_mm: float
    resistance_per_km_ohm: float
    typical_use: str


COPPER_SPECS = [
    CopperCableSpec(0.35, 355.2, "Verzweigerkabel (VzK)"),
    CopperCableSpec(0.40, 270.0, "Verzweigerkabel (VzK)"),
    CopperCableSpec(0.50, 172.8, "Hauptkabel (Hk)"),
    CopperCableSpec(0.60, 119.0, "Hauptkabel (Hk)"),
    CopperCableSpec(0.80, 67.0, "Ortsverbindungskabel (OVk)"),
]

# Maximum loop resistance for planning
MAX_LOOP_RESISTANCE_OHM = 1200
PLANNING_RESERVE_M = 200

# Near-field (Nahbereich) definition
NAHBEREICH_MAX_LENGTH_M = 550


# ============================================================
# DEPLOYMENT ARCHITECTURE TYPES
# ============================================================

class DeploymentType(Enum):
    """FTTH deployment architecture types."""
    MICRODUCT = "mikrorohrkonzept"      # SpeedNet microduct, standard
    CONVENTIONAL = "konventionell"       # Traditional cables with splice closures
    AERIAL = "oberirdisch"               # Aerial/overhead deployment


@dataclass
class DeploymentConfig:
    """Deployment architecture configuration."""
    type: DeploymentType
    description: str
    max_distance_m: int
    use_case: str


DEPLOYMENT_CONFIGS = {
    DeploymentType.MICRODUCT: DeploymentConfig(
        DeploymentType.MICRODUCT,
        "SpeedNet Mikrorohrkonzept - muffenlose Verbindung",
        750,
        "Regelausbau (standard deployment)"
    ),
    DeploymentType.CONVENTIONAL: DeploymentConfig(
        DeploymentType.CONVENTIONAL,
        "Konventionelles Gf-Verzweigernetz mit Abzweigmuffen",
        9999,  # No practical limit
        "Trassenlänge > 750m zwischen Gf-NVt und Gf-AP"
    ),
    DeploymentType.AERIAL: DeploymentConfig(
        DeploymentType.AERIAL,
        "Oberirdisches Gf-Verzweigernetz mit Luftkabeln",
        9999,
        "Rural areas, existing pole infrastructure"
    ),
}


# ============================================================
# EXPANSION FACTORS (Ausbaufaktor)
# ============================================================

EXPANSION_FACTORS = {
    # WE per building → VzK pairs per WE
    "1": 2.0,      # Single family homes
    "2-9": 1.6,    # Small multi-family
    "10+": 1.3,    # Large multi-family / commercial
}


# ============================================================
# MONITORING SYSTEMS
# ============================================================

@dataclass
class MonitoringSystem:
    """Network monitoring system specification."""
    name: str
    type: str
    measurement: str
    threshold_db: float


MONITORING_SYSTEMS = [
    MonitoringSystem("GfÜS", "fiber", "attenuation", 3.0),  # Heavy fault
    MonitoringSystem("GfÜS", "fiber", "water_sensor", 0.5),  # Light fault
    MonitoringSystem("sDLÜA", "copper", "air_pressure", 1500),  # hPa
]


# ============================================================
# COST ESTIMATION HELPERS
# ============================================================

def estimate_capex_per_home(
    distance_to_nvt_m: int,
    building_size_we: int,
    deployment_type: DeploymentType = DeploymentType.MICRODUCT,
    terrain_factor: float = 1.0
) -> dict:
    """
    Estimate CAPEX per home based on Telekom planning parameters.
    
    This is a simplified model - real costs depend on many factors.
    Base costs are estimates for illustration.
    """
    # Base costs (€) - illustrative
    BASE_COST_PER_HOME = 600
    COST_PER_METER_MICRODUCT = 25
    COST_PER_METER_CONVENTIONAL = 45
    COST_PER_METER_AERIAL = 20
    
    # Distance cost
    if deployment_type == DeploymentType.MICRODUCT:
        distance_cost = distance_to_nvt_m * COST_PER_METER_MICRODUCT / building_size_we
    elif deployment_type == DeploymentType.CONVENTIONAL:
        distance_cost = distance_to_nvt_m * COST_PER_METER_CONVENTIONAL / building_size_we
    else:
        distance_cost = distance_to_nvt_m * COST_PER_METER_AERIAL / building_size_we
    
    # Splitter cost
    if building_size_we <= 3:
        splitter_cost = 50
    elif building_size_we <= 8:
        splitter_cost = 80
    else:
        splitter_cost = 120
    
    # Total
    total = (BASE_COST_PER_HOME + distance_cost + splitter_cost) * terrain_factor
    
    return {
        "base_cost": BASE_COST_PER_HOME,
        "distance_cost": round(distance_cost),
        "splitter_cost": splitter_cost,
        "terrain_factor": terrain_factor,
        "total_per_home": round(total),
        "deployment_type": deployment_type.value,
    }


def get_bitrate_recommendation(homes: int, adoption_pct: float) -> dict:
    """
    Recommend splitting factor based on expected concurrent users.
    
    Based on Telekom GPON planning guidelines.
    """
    concurrent_users = homes * (adoption_pct / 100) * 0.3  # 30% concurrency
    
    gpon = GPONSpecs()
    
    recommendations = []
    for split in [8, 16, 32]:
        bitrate = gpon.get_bitrate_per_user(split)
        recommendations.append({
            "splitting": f"1:{split}",
            "downstream_mbps": bitrate["downstream_mbps"],
            "upstream_mbps": bitrate["upstream_mbps"],
            "max_users": split,
            "suitable": concurrent_users <= split,
        })
    
    suitable = [r for r in recommendations if r["suitable"]]
    return {
        "concurrent_users_estimate": round(concurrent_users),
        "recommended": suitable[0] if suitable else recommendations[-1],
        "all_options": recommendations,
    }


# ============================================================
# GLOSSARY
# ============================================================

TELEKOM_GLOSSARY = {
    "AsB": "Anschlussbereich - subscriber access area",
    "HVt": "Hauptverteiler - main distribution frame",
    "KVz": "Kabelverzweiger - cable distribution cabinet",
    "Gf-NVt": "Glasfaser-Netzverteiler - fiber network distributor",
    "Gf-AP": "Glasfaser-Abschlusspunkt - fiber termination point",
    "ONT": "Optical Network Terminal - customer device",
    "OLT": "Optical Line Terminal - central office equipment",
    "GPON": "Gigabit Passive Optical Network",
    "WE": "Wohneinheit - residential unit (apartment)",
    "SNR": "SpeedNet-Rohr - SpeedNet microduct",
    "SNRV": "SpeedNet-Rohrverband - SpeedNet microduct bundle",
    "VzK": "Verzweigerkabel - distribution cable",
    "Hk": "Hauptkabel - main cable",
    "E&MMS": "Easy & Modular Mechanical Splice - splice system",
    "Nb": "Nahbereich - near-field area (≤550m from HVt)",
}


if __name__ == "__main__":
    # Demo
    print("=== GPON Specifications ===")
    print(f"Max distance: {GPONSpecs.MAX_DISTANCE_KM} km")
    print(f"Planning distance: {GPONSpecs.PLANNING_DISTANCE_KM} km")
    print(f"Max attenuation: {GPONSpecs.MAX_ATTENUATION_DB} dB")
    
    print("\n=== Bitrate per User (1:32 split) ===")
    br = GPONSpecs.get_bitrate_per_user(32)
    print(f"Downstream: {br['downstream_mbps']} Mbit/s")
    print(f"Upstream: {br['upstream_mbps']} Mbit/s")
    
    print("\n=== Splitter Attenuation ===")
    for ratio, spec in SPLITTER_SPECS.items():
        print(f"{ratio}: {spec.attenuation_db} dB")
    
    print("\n=== CAPEX Estimate (500m, 8 WE) ===")
    capex = estimate_capex_per_home(500, 8)
    print(f"Total per home: €{capex['total_per_home']}")
