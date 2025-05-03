# Interface Element Creation Guide

## Overview
Interface elements model the interaction between beam elements (like pipes or culverts) and 
surrounding soil. This guide explains how to create and work with interface elements in the CANDE Editor.

## Step-by-Step Process

1. **Select Beam Elements**
   - Use Ctrl+Click or drag selection to select beam elements where interfaces are needed
   - Focus on areas where beams connect to soil (2D elements)

2. **Set Friction Coefficient**
   - Enter the desired friction value in the "Friction" input field
   - Values typically range from 0.0 (frictionless) to 1.0 (high friction)

3. **Create Interfaces**
   - Click the "Create Interfaces" button
   - Interface elements will be created at shared nodes between beams
   - Direction is automatically calculated based on beam geometry

4. **Verify Results**
   - Interface elements appear as diamond shapes at beam joints
   - Red arrows show the normal force direction
   - Green dashed lines show the interface plane
   - Material numbers and angles are displayed for reference

5. **Save Your Work**
   - Interface material properties are automatically saved to the CANDE file
   - Each unique friction/angle combination gets its own material ID

## Notes
- Interfaces inherit the minimum step number from connected 2D elements
- Interface properties cannot be modified directly after creation
- If you need different friction values, create new interfaces with the desired properties