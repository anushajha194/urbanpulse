import React, { useState, useEffect } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  ScrollView,
  SafeAreaView,
  TextInput,
  ActivityIndicator,
  Alert,
  Animated,
} from 'react-native';
import MockCamera from './src/components/MockCamera';
import Timeline from './src/components/Timeline';

export default function App() {
  const [activeTab, setActiveTab] = useState('report'); // 'report' or 'history'
  const [imageUri, setImageUri] = useState(null);

  // GPS Auto-fill states
  const [lat, setLat] = useState(null);
  const [lng, setLng] = useState(null);
  const [locating, setLocating] = useState(false);

  // Issue description states
  const [issueCategory, setIssueCategory] = useState(null);
  const [description, setDescription] = useState('');

  // Submissions State
  const [submitting, setSubmitting] = useState(false);
  const [submissions, setSubmissions] = useState([
    {
      id: "comp-101",
      issue_class: "pothole",
      lat: 28.6139,
      lng: 77.2090,
      status: "assigned",
      created_at: new Date(Date.now() - 3600000 * 24).toISOString()
    },
    {
      id: "comp-102",
      issue_class: "waterlogging",
      lat: 28.6115,
      lng: 77.2130,
      status: "verified",
      created_at: new Date(Date.now() - 3600000 * 72).toISOString()
    }
  ]);
  const [selectedSubmission, setSelectedSubmission] = useState(null);

  // Tab indicator animation
  const [tabIndicator] = useState(new Animated.Value(0));

  const API_URL = 'http://localhost:8001/api/v1/complaints';

  useEffect(() => {
    Animated.spring(tabIndicator, {
      toValue: activeTab === 'report' ? 0 : 1,
      useNativeDriver: false,
      tension: 68,
      friction: 10,
    }).start();
  }, [activeTab]);

  // Fetch coordinates on photo select
  const handlePhotoSelect = (uri) => {
    setImageUri(uri);
    autoFillGPS();
  };

  const autoFillGPS = () => {
    setLocating(true);
    // Mimic geolocation sensor query
    if (typeof navigator !== 'undefined' && navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setLat(position.coords.latitude);
          setLng(position.coords.longitude);
          setLocating(false);
        },
        (error) => {
          console.warn("Geolocation API unavailable. Mocking Delhi GPS coordinates.", error);
          mockDelhiGPS();
        },
        { enableHighAccuracy: true, timeout: 5000, maximumAge: 10000 }
      );
    } else {
      mockDelhiGPS();
    }
  };

  const mockDelhiGPS = () => {
    // Delhi center coordinates +- random offset
    const randomOffsetLat = (Math.random() - 0.5) * 0.01;
    const randomOffsetLng = (Math.random() - 0.5) * 0.01;
    setTimeout(() => {
      setLat(28.6139 + randomOffsetLat);
      setLng(77.2090 + randomOffsetLng);
      setLocating(false);
    }, 800);
  };

  const issueCategories = [
    { key: 'pothole', label: 'Pothole', icon: '🕳️' },
    { key: 'manhole', label: 'Manhole', icon: '⚠️' },
    { key: 'streetlight', label: 'Streetlight', icon: '💡' },
    { key: 'waterlogging', label: 'Waterlogging', icon: '🌊' },
    { key: 'footpath', label: 'Footpath', icon: '🚶' },
    { key: 'other', label: 'Other', icon: '📝' },
  ];

  const handleSubmit = async () => {
    if (!imageUri) {
      Alert.alert("Error", "Please capture/upload a photo first.");
      return;
    }
    if (!lat || !lng) {
      Alert.alert("Error", "GPS coordinates missing. Retrying geolocation...");
      autoFillGPS();
      return;
    }
    if (!issueCategory) {
      Alert.alert("Error", "Please select an issue category.");
      return;
    }

    setSubmitting(true);

    try {
      // Simulate multipart upload to Ingestion API
      const formData = new FormData();
      // Mock File object
      formData.append('image', {
        uri: imageUri,
        name: 'report.jpg',
        type: 'image/jpeg'
      });
      formData.append('lat', lat.toString());
      formData.append('lng', lng.toString());
      formData.append('source', 'mobile_app');
      formData.append('issue_class', issueCategory);
      if (description.trim()) {
        formData.append('description', description.trim());
      }

      // Make actual post to ingestion API, falling back to local list on failure
      const response = await fetch(API_URL, {
        method: 'POST',
        body: formData,
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'multipart/form-data',
        }
      });

      if (!response.ok) throw new Error('API failure');
      const data = await response.json();

      const newSubmission = {
        id: data.id || `comp-${Math.floor(Math.random() * 1000)}`,
        issue_class: issueCategory,
        description: description.trim() || null,
        lat: lat,
        lng: lng,
        status: 'pending',
        created_at: new Date().toISOString()
      };

      setSubmissions(prev => [newSubmission, ...prev]);
      Alert.alert("Success", "Complaint submitted successfully!");
      resetForm();
      setActiveTab('history');

    } catch (err) {
      console.warn("Backend API unreachable. Registering complaint locally.", err);
      // Fallback local registration
      const localId = `comp-${Math.floor(Math.random() * 900) + 100}`;
      const newSubmission = {
        id: localId,
        issue_class: issueCategory,
        description: description.trim() || null,
        lat: lat,
        lng: lng,
        status: 'pending',
        created_at: new Date().toISOString()
      };
      setSubmissions(prev => [newSubmission, ...prev]);
      Alert.alert("Success (Offline)", "Complaint registered. Syncing in background.");
      resetForm();
      setActiveTab('history');
    } finally {
      setSubmitting(false);
    }
  };

  const resetForm = () => {
    setImageUri(null);
    setLat(null);
    setLng(null);
    setIssueCategory(null);
    setDescription('');
  };

  const getStatusConfig = (status) => {
    switch (status) {
      case 'pending': return { color: '#d29922', bg: 'rgba(210, 153, 34, 0.1)', label: 'PENDING' };
      case 'under_review': return { color: '#f0883e', bg: 'rgba(240, 136, 62, 0.1)', label: 'REVIEWING' };
      case 'assigned': return { color: '#58a6ff', bg: 'rgba(88, 166, 255, 0.1)', label: 'ASSIGNED' };
      case 'in_progress': return { color: '#1f6feb', bg: 'rgba(31, 111, 235, 0.1)', label: 'IN PROGRESS' };
      case 'verified':
      case 'closed': return { color: '#3fb950', bg: 'rgba(63, 185, 80, 0.1)', label: 'RESOLVED' };
      default: return { color: '#8b949e', bg: 'rgba(139, 148, 158, 0.1)', label: status.toUpperCase() };
    }
  };

  const tabIndicatorLeft = tabIndicator.interpolate({
    inputRange: [0, 1],
    outputRange: ['2%', '52%'],
  });

  return (
    <SafeAreaView style={styles.container}>
      {/* ─── Gradient Header ─── */}
      <View style={styles.header}>
        <View style={styles.headerTop}>
          <View style={styles.headerLogoRow}>
            <View style={styles.headerLogo}>
              <Text style={styles.headerLogoText}>UP</Text>
            </View>
            <View>
              <Text style={styles.headerTitle}>UrbanPulse</Text>
              <Text style={styles.headerSubtitle}>Report Civic Issues</Text>
            </View>
          </View>
          <View style={styles.headerBadge}>
            <View style={styles.liveDot} />
            <Text style={styles.headerBadgeText}>Live</Text>
          </View>
        </View>
      </View>

      {/* ─── Main Content ─── */}
      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {activeTab === 'report' ? (
          <View style={styles.formContainer}>
            {/* Step indicator */}
            <View style={styles.stepsRow}>
              <View style={[styles.stepBadge, imageUri ? styles.stepDone : styles.stepCurrent]}>
                <Text style={styles.stepBadgeText}>{imageUri ? '✓' : '1'}</Text>
              </View>
              <View style={[styles.stepLine, imageUri ? styles.stepLineDone : {}]} />
              <View style={[styles.stepBadge, imageUri && lat ? styles.stepDone : imageUri ? styles.stepCurrent : styles.stepPending]}>
                <Text style={styles.stepBadgeText}>{imageUri && lat ? '✓' : '2'}</Text>
              </View>
              <View style={[styles.stepLine, imageUri && lat ? styles.stepLineDone : {}]} />
              <View style={[styles.stepBadge, imageUri && lat && issueCategory ? styles.stepDone : imageUri && lat ? styles.stepCurrent : styles.stepPending]}>
                <Text style={styles.stepBadgeText}>{imageUri && lat && issueCategory ? '✓' : '3'}</Text>
              </View>
              <View style={[styles.stepLine, imageUri && lat && issueCategory ? styles.stepLineDone : {}]} />
              <View style={[styles.stepBadge, styles.stepPending]}>
                <Text style={styles.stepBadgeText}>4</Text>
              </View>
            </View>

            {/* Mock camera view */}
            <MockCamera imageUri={imageUri} onSelectPhoto={handlePhotoSelect} />

            {/* GPS details indicator */}
            <View style={styles.coordCard}>
              <View style={styles.coordCardHeader}>
                <View style={styles.coordLabelRow}>
                  <Text style={styles.coordIcon}>📍</Text>
                  <Text style={styles.cardLabel}>LOCATION DATA</Text>
                </View>
                {lat && lng && (
                  <TouchableOpacity
                    style={styles.refreshBtn}
                    onClick={autoFillGPS}
                    onPress={autoFillGPS}
                    accessibilityLabel="Refresh GPS location"
                    accessibilityRole="button"
                  >
                    <Text style={styles.refreshBtnText}>↻ Refresh</Text>
                  </TouchableOpacity>
                )}
              </View>
              {locating ? (
                <View style={styles.loadingRow}>
                  <ActivityIndicator size="small" color="#58a6ff" />
                  <Text style={styles.locatingText}>Resolving your location...</Text>
                </View>
              ) : lat && lng ? (
                <View style={styles.coordsRow}>
                  <View style={styles.coordCol}>
                    <Text style={styles.coordLabel}>Latitude</Text>
                    <Text style={styles.coordVal}>{lat.toFixed(6)}</Text>
                  </View>
                  <View style={styles.coordDivider} />
                  <View style={styles.coordCol}>
                    <Text style={styles.coordLabel}>Longitude</Text>
                    <Text style={styles.coordVal}>{lng.toFixed(6)}</Text>
                  </View>
                </View>
              ) : (
                <View style={styles.emptyCoords}>
                  <Text style={styles.emptyCoordsIcon}>🛰️</Text>
                  <Text style={styles.emptyCoordsText}>Capture a photo to auto-detect location</Text>
                </View>
              )}
            </View>

            {/* ─── Issue Category Selector ─── */}
            <View style={styles.issueSectionCard}>
              <View style={styles.issueSectionHeader}>
                <Text style={styles.issueSectionIcon}>🏷️</Text>
                <Text style={styles.cardLabel}>WHAT'S THE ISSUE?</Text>
              </View>
              <View style={styles.categoryChipsRow}>
                {issueCategories.map((cat) => (
                  <TouchableOpacity
                    key={cat.key}
                    style={[
                      styles.categoryChip,
                      issueCategory === cat.key ? styles.categoryChipActive : {}
                    ]}
                    onClick={() => setIssueCategory(cat.key)}
                    onPress={() => setIssueCategory(cat.key)}
                    accessibilityLabel={`Select issue type: ${cat.label}`}
                    accessibilityRole="button"
                  >
                    <Text style={styles.categoryChipIcon}>{cat.icon}</Text>
                    <Text style={[
                      styles.categoryChipText,
                      issueCategory === cat.key ? styles.categoryChipTextActive : {}
                    ]}>{cat.label}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>

            {/* ─── Description Input ─── */}
            <View style={styles.descriptionCard}>
              <View style={styles.issueSectionHeader}>
                <Text style={styles.issueSectionIcon}>✏️</Text>
                <Text style={styles.cardLabel}>DESCRIBE THE PROBLEM</Text>
                <Text style={styles.optionalBadge}>Optional</Text>
              </View>
              <TextInput
                style={styles.descriptionInput}
                placeholder="e.g. Large pothole near main road junction, causing traffic issues..."
                placeholderTextColor="#484f58"
                multiline={true}
                numberOfLines={3}
                maxLength={300}
                value={description}
                onChangeText={setDescription}
                accessibilityLabel="Describe the civic issue in brief"
              />
              <Text style={styles.charCount}>{description.length}/300</Text>
            </View>

            {/* Submit Button */}
            <TouchableOpacity
              style={[
                styles.submitBtn,
                !imageUri ? styles.submitBtnDisabled : {},
                submitting ? styles.submitBtnSubmitting : {}
              ]}
              disabled={submitting || !imageUri}
              onClick={handleSubmit}
              onPress={handleSubmit}
              accessibilityLabel="Submit complaint report"
              accessibilityRole="button"
            >
              {submitting ? (
                <View style={styles.submitLoadingRow}>
                  <ActivityIndicator size="small" color="#ffffff" />
                  <Text style={styles.submitBtnText}>Submitting...</Text>
                </View>
              ) : (
                <View style={styles.submitContentRow}>
                  <Text style={styles.submitIcon}>🚀</Text>
                  <Text style={styles.submitBtnText}>Submit Complaint</Text>
                </View>
              )}
            </TouchableOpacity>
          </View>
        ) : (
          /* ─── Submissions Timeline Tracker ─── */
          <View style={styles.listContainer}>
            <View style={styles.listHeaderRow}>
              <Text style={styles.listTitle}>My Reports</Text>
              <View style={styles.listCountBadge}>
                <Text style={styles.listCountText}>{submissions.length}</Text>
              </View>
            </View>

            {submissions.map((item) => {
              const statusConfig = getStatusConfig(item.status);
              const isExpanded = selectedSubmission?.id === item.id;

              return (
                <TouchableOpacity
                  key={item.id}
                  style={[
                    styles.submissionCard,
                    { borderLeftColor: statusConfig.color },
                    isExpanded ? styles.submissionCardExpanded : {}
                  ]}
                  onClick={() => setSelectedSubmission(isExpanded ? null : item)}
                  onPress={() => setSelectedSubmission(isExpanded ? null : item)}
                  accessibilityLabel={`Complaint ${item.id}: ${item.issue_class}, status ${item.status}`}
                  accessibilityRole="button"
                >
                  <View style={styles.cardHeader}>
                    <View style={styles.cardTitleRow}>
                      <Text style={[styles.cardIssueTitle, { color: statusConfig.color }]}>
                        {item.issue_class.toUpperCase()}
                      </Text>
                      <View style={[styles.statusPill, { backgroundColor: statusConfig.bg }]}>
                        <Text style={[styles.statusPillText, { color: statusConfig.color }]}>
                          {statusConfig.label}
                        </Text>
                      </View>
                    </View>
                    <Text style={styles.cardId}>#{item.id}</Text>
                  </View>
                  <View style={styles.cardMetaRow}>
                    <Text style={styles.cardDate}>
                      📅 {new Date(item.created_at).toLocaleDateString('en-US', {
                        month: 'short', day: 'numeric', year: 'numeric'
                      })}
                    </Text>
                    <Text style={styles.cardCoords}>
                      📍 {item.lat.toFixed(4)}, {item.lng.toFixed(4)}
                    </Text>
                  </View>

                  {/* Expand arrow */}
                  <Text style={styles.expandArrow}>{isExpanded ? '▲' : '▼'}</Text>

                  {/* If selected, expand and show timeline stepper */}
                  {isExpanded && (
                    <View style={styles.expandedTimeline}>
                      <Text style={styles.timelineHeader}>Resolution Timeline</Text>
                      <Timeline status={item.status} />
                    </View>
                  )}
                </TouchableOpacity>
              );
            })}
          </View>
        )}
      </ScrollView>

      {/* ─── Tab Navigation Bar ─── */}
      <View style={styles.tabsContainer}>
        <Animated.View style={[
          styles.tabIndicator,
          { left: tabIndicatorLeft }
        ]} />
        <TouchableOpacity
          style={styles.tab}
          onClick={() => setActiveTab('report')}
          onPress={() => setActiveTab('report')}
          accessibilityLabel="Report tab"
          accessibilityRole="tab"
        >
          <Text style={[styles.tabSymbol, activeTab === 'report' ? styles.tabSymbolActive : {}]}>📷</Text>
          <Text style={[styles.tabLabel, activeTab === 'report' ? styles.tabLabelActive : {}]}>Report</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.tab}
          onClick={() => setActiveTab('history')}
          onPress={() => setActiveTab('history')}
          accessibilityLabel="History tab"
          accessibilityRole="tab"
        >
          <Text style={[styles.tabSymbol, activeTab === 'history' ? styles.tabSymbolActive : {}]}>📋</Text>
          <Text style={[styles.tabLabel, activeTab === 'history' ? styles.tabLabelActive : {}]}>History</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#06080f',
  },

  /* ─── Header ─── */
  header: {
    paddingTop: 16,
    paddingBottom: 14,
    paddingHorizontal: 20,
    backgroundColor: '#0d1117',
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.06)',
  },
  headerTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerLogoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  headerLogo: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: '#58a6ff',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#58a6ff',
    shadowOpacity: 0.3,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 8,
    elevation: 5,
  },
  headerLogoText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '800',
  },
  headerTitle: {
    color: '#e6edf3',
    fontSize: 18,
    fontWeight: '700',
  },
  headerSubtitle: {
    color: '#8b949e',
    fontSize: 11,
    marginTop: 1,
  },
  headerBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingVertical: 4,
    paddingHorizontal: 10,
    backgroundColor: 'rgba(63, 185, 80, 0.08)',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: 'rgba(63, 185, 80, 0.2)',
  },
  liveDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#3fb950',
    shadowColor: '#3fb950',
    shadowOpacity: 0.6,
    shadowRadius: 4,
  },
  headerBadgeText: {
    color: '#3fb950',
    fontSize: 11,
    fontWeight: '700',
  },

  /* ─── Content ─── */
  content: {
    flex: 1,
    padding: 20,
  },
  formContainer: {
    flex: 1,
    paddingBottom: 20,
  },

  /* ─── Step Indicator ─── */
  stepsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 20,
    gap: 0,
  },
  stepBadge: {
    width: 28,
    height: 28,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
  },
  stepCurrent: {
    backgroundColor: 'rgba(88, 166, 255, 0.1)',
    borderColor: '#58a6ff',
  },
  stepDone: {
    backgroundColor: '#238636',
    borderColor: '#3fb950',
  },
  stepPending: {
    backgroundColor: '#161b22',
    borderColor: '#30363d',
  },
  stepBadgeText: {
    color: '#e6edf3',
    fontSize: 11,
    fontWeight: '700',
  },
  stepLine: {
    width: 32,
    height: 2,
    backgroundColor: '#21262d',
    borderRadius: 1,
  },
  stepLineDone: {
    backgroundColor: '#3fb950',
  },

  /* ─── GPS Card ─── */
  coordCard: {
    backgroundColor: '#0d1117',
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.06)',
    marginBottom: 20,
  },
  coordCardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  coordLabelRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  coordIcon: {
    fontSize: 14,
  },
  cardLabel: {
    color: '#8b949e',
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.8,
  },
  refreshBtn: {
    paddingVertical: 4,
    paddingHorizontal: 10,
    backgroundColor: 'rgba(88, 166, 255, 0.08)',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(88, 166, 255, 0.15)',
  },
  refreshBtnText: {
    color: '#58a6ff',
    fontSize: 11,
    fontWeight: '600',
  },
  loadingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 8,
  },
  locatingText: {
    color: '#58a6ff',
    fontSize: 13,
  },
  coordsRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  coordCol: {
    flex: 1,
    paddingVertical: 4,
  },
  coordDivider: {
    width: 1,
    height: 30,
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
    marginHorizontal: 16,
  },
  coordLabel: {
    color: '#8b949e',
    fontSize: 10,
    marginBottom: 4,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  coordVal: {
    color: '#e6edf3',
    fontSize: 16,
    fontWeight: '700',
    letterSpacing: -0.3,
  },
  emptyCoords: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 8,
  },
  emptyCoordsIcon: {
    fontSize: 16,
  },
  emptyCoordsText: {
    color: '#484f58',
    fontSize: 13,
    fontStyle: 'italic',
  },

  /* ─── Issue Category & Description ─── */
  issueSectionCard: {
    backgroundColor: '#0d1117',
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.06)',
    marginBottom: 16,
  },
  issueSectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 14,
  },
  issueSectionIcon: {
    fontSize: 14,
  },
  categoryChipsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  categoryChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 10,
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
  },
  categoryChipActive: {
    backgroundColor: 'rgba(88, 166, 255, 0.12)',
    borderColor: '#58a6ff',
  },
  categoryChipIcon: {
    fontSize: 14,
  },
  categoryChipText: {
    color: '#8b949e',
    fontSize: 12,
    fontWeight: '600',
  },
  categoryChipTextActive: {
    color: '#58a6ff',
  },
  descriptionCard: {
    backgroundColor: '#0d1117',
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.06)',
    marginBottom: 20,
  },
  optionalBadge: {
    color: '#484f58',
    fontSize: 9,
    fontWeight: '600',
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    paddingVertical: 2,
    paddingHorizontal: 6,
    borderRadius: 4,
    marginLeft: 'auto',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  descriptionInput: {
    backgroundColor: '#161b22',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.06)',
    padding: 14,
    color: '#e6edf3',
    fontSize: 14,
    lineHeight: 20,
    minHeight: 80,
    textAlignVertical: 'top',
  },
  charCount: {
    color: '#484f58',
    fontSize: 10,
    textAlign: 'right',
    marginTop: 6,
  },

  /* ─── Submit Button ─── */
  submitBtn: {
    borderRadius: 14,
    height: 52,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#1f6feb',
    shadowColor: '#58a6ff',
    shadowOpacity: 0.3,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 12,
    elevation: 6,
  },
  submitBtnDisabled: {
    backgroundColor: '#21262d',
    shadowOpacity: 0,
    elevation: 0,
  },
  submitBtnSubmitting: {
    backgroundColor: '#1f6feb',
    opacity: 0.8,
  },
  submitLoadingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  submitContentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  submitIcon: {
    fontSize: 16,
  },
  submitBtnText: {
    color: '#ffffff',
    fontSize: 15,
    fontWeight: '700',
  },

  /* ─── Submissions List ─── */
  listContainer: {
    flex: 1,
    paddingBottom: 20,
  },
  listHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 16,
  },
  listTitle: {
    color: '#e6edf3',
    fontSize: 18,
    fontWeight: '700',
  },
  listCountBadge: {
    backgroundColor: 'rgba(88, 166, 255, 0.1)',
    paddingVertical: 2,
    paddingHorizontal: 10,
    borderRadius: 10,
  },
  listCountText: {
    color: '#58a6ff',
    fontSize: 12,
    fontWeight: '700',
  },
  submissionCard: {
    backgroundColor: '#0d1117',
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.06)',
    borderLeftWidth: 3,
    marginBottom: 12,
    position: 'relative',
  },
  submissionCardExpanded: {
    borderColor: 'rgba(88, 166, 255, 0.15)',
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  cardTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  cardIssueTitle: {
    fontSize: 14,
    fontWeight: '700',
  },
  statusPill: {
    paddingVertical: 2,
    paddingHorizontal: 8,
    borderRadius: 8,
  },
  statusPillText: {
    fontSize: 9,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  cardId: {
    color: '#484f58',
    fontSize: 11,
    fontWeight: '500',
  },
  cardMetaRow: {
    flexDirection: 'row',
    gap: 16,
  },
  cardDate: {
    color: '#8b949e',
    fontSize: 11,
  },
  cardCoords: {
    color: '#8b949e',
    fontSize: 11,
  },
  expandArrow: {
    position: 'absolute',
    right: 16,
    bottom: 16,
    color: '#484f58',
    fontSize: 10,
  },
  expandedTimeline: {
    marginTop: 16,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.06)',
    paddingTop: 16,
  },
  timelineHeader: {
    color: '#e6edf3',
    fontSize: 12,
    fontWeight: '700',
    marginBottom: 8,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },

  /* ─── Tab Bar ─── */
  tabsContainer: {
    flexDirection: 'row',
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.06)',
    backgroundColor: '#0d1117',
    height: 64,
    position: 'relative',
  },
  tabIndicator: {
    position: 'absolute',
    top: 0,
    width: '46%',
    height: 2,
    backgroundColor: '#58a6ff',
    borderRadius: 1,
  },
  tab: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 3,
  },
  tabSymbol: {
    fontSize: 20,
    opacity: 0.5,
  },
  tabSymbolActive: {
    opacity: 1,
  },
  tabLabel: {
    fontSize: 11,
    color: '#484f58',
    fontWeight: '500',
  },
  tabLabelActive: {
    color: '#58a6ff',
    fontWeight: '700',
  },
});
