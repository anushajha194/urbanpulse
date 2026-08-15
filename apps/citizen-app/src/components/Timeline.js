import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function Timeline({ status }) {
  const steps = [
    { key: 'submitted', label: 'Submitted', icon: '📤', desc: 'Report received' },
    { key: 'assigned', label: 'Assigned', icon: '👷', desc: 'Department notified' },
    { key: 'in_progress', label: 'In Progress', icon: '🔧', desc: 'Work underway' },
    { key: 'verified', label: 'Resolved', icon: '✅', desc: 'Issue resolved' }
  ];

  // Map database statuses to step indexes
  const getStepIndex = (currStatus) => {
    switch (currStatus) {
      case 'pending':
      case 'under_review':
        return 0;
      case 'assigned':
        return 1;
      case 'in_progress':
        return 2;
      case 'verified':
      case 'closed':
        return 3;
      default:
        return 0;
    }
  };

  const activeIndex = getStepIndex(status);

  return (
    <View
      style={styles.container}
      accessibilityLabel={`Resolution timeline: currently at step ${activeIndex + 1} of ${steps.length}`}
      accessibilityRole="progressbar"
    >
      {steps.map((step, idx) => {
        const isCompleted = idx <= activeIndex;
        const isActive = idx === activeIndex;
        const isLast = idx === steps.length - 1;

        return (
          <View key={step.key} style={styles.stepWrapper}>
            {/* Step Marker Node */}
            <View style={styles.nodeColumn}>
              <View style={[
                styles.circle,
                isCompleted ? styles.circleCompleted : styles.circlePending,
                isActive ? styles.circleActive : {}
              ]}>
                {isCompleted ? (
                  <Text style={styles.stepIcon}>{step.icon}</Text>
                ) : (
                  <Text style={styles.stepNum}>{idx + 1}</Text>
                )}
              </View>
              {/* Connector line */}
              {!isLast && (
                <View style={[
                  styles.line,
                  idx < activeIndex ? styles.lineCompleted : styles.linePending
                ]} />
              )}
            </View>

            {/* Label and Info */}
            <View style={styles.labelColumn}>
              <Text style={[
                styles.label,
                isCompleted ? styles.labelCompleted : styles.labelPending,
                isActive ? styles.labelActive : {}
              ]}>
                {step.label}
              </Text>
              <Text style={[
                styles.subtext,
                isActive ? styles.subtextActive : {}
              ]}>
                {isActive 
                  ? `● ${step.desc}` 
                  : idx < activeIndex 
                    ? `✓ ${step.desc}` 
                    : step.desc}
              </Text>
            </View>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingVertical: 12,
    paddingHorizontal: 8,
  },
  stepWrapper: {
    flexDirection: 'row',
    minHeight: 62,
  },
  nodeColumn: {
    alignItems: 'center',
    marginRight: 16,
  },
  circle: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 10,
    borderWidth: 2,
  },
  circlePending: {
    backgroundColor: '#161b22',
    borderColor: '#30363d',
  },
  circleCompleted: {
    backgroundColor: '#238636',
    borderColor: '#3fb950',
  },
  circleActive: {
    borderColor: '#58a6ff',
    borderWidth: 3,
    backgroundColor: '#0d1117',
    shadowColor: '#58a6ff',
    shadowOpacity: 0.4,
    shadowOffset: { width: 0, height: 0 },
    shadowRadius: 8,
    elevation: 5,
  },
  stepIcon: {
    fontSize: 14,
  },
  stepNum: {
    color: '#484f58',
    fontSize: 12,
    fontWeight: '700',
  },
  line: {
    width: 2,
    flex: 1,
    marginVertical: 4,
    borderRadius: 1,
  },
  linePending: {
    backgroundColor: '#21262d',
  },
  lineCompleted: {
    backgroundColor: '#3fb950',
  },
  labelColumn: {
    justifyContent: 'center',
    paddingBottom: 16,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
  },
  labelPending: {
    color: '#484f58',
  },
  labelCompleted: {
    color: '#e6edf3',
  },
  labelActive: {
    color: '#58a6ff',
  },
  subtext: {
    fontSize: 11,
    color: '#484f58',
    marginTop: 2,
  },
  subtextActive: {
    color: '#58a6ff',
    fontWeight: '500',
  },
});
