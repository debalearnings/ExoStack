from setuptools import find_packages, setup
from glob import glob
import os

package_name = 'exo_stack'

# Function to recursively collect all files in a folder
def recursive_glob(folder):
    return [f for f in glob(os.path.join(folder, '**/*'), recursive=True) if os.path.isfile(f)]

# List all resource folders to include
resource_folders = ['config', 'launch', 'util', 'meshes', 'algos']

# Collect all files from resource folders
data_files = [
    ('share/ament_index/resource_index/packages', [f'resource/{package_name}']),
    ('share/' + package_name, ['package.xml'])
]

for folder in resource_folders:
    if os.path.exists(folder):
        files = recursive_glob(folder)
        # Install files preserving folder structure under share/package_name
        for f in files:
            target = os.path.join('share', package_name, os.path.relpath(f, start='.'))
            data_files.append((os.path.dirname(target), [f]))

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=data_files,
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Debadrata Sarkar',
    description='ExoCore: generic ROS 2 nodes of ExoStack for wearable robots',
    license='PolyForm-Noncommercial-1.0.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'hubr=exo_stack.hub_r_emulator:main',
            'hubl=exo_stack.hub_l_emulator:main',
            'hub3=exo_stack.hub_3_emulator:main',
            'hub4=exo_stack.hub_4_emulator:main',
            'sync=exo_stack.sync_with_trigger:main',
            'gait_event_detector=exo_stack.gait_event_detector:main',
            'mplanner=exo_stack.mplanner:main',
            'gaiteventdetectorlaunch=exo_stack.gait_event_detector_launch:main',
            'mplannerlaunch=exo_stack.mplanner_launch:main',
            'actuation_profile=exo_stack.profile:main',
            'actuation_profile_launch=exo_stack.actuation_profile_launch:main',
            'modegui=exo_stack.mode_gui:main',
            'hil=exo_stack.hil:main',
            'hil_launch=exo_stack.hil_launch:main',
            'cost=exo_stack.cost_updated:main',
            'cost_launch=exo_stack.cost_launch:main',

        ],
    },
)
