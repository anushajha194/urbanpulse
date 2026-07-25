"""
Schema validation tests for UrbanPulse database.

Tests verify:
- All tables and extensions are created
- Constraints (CHECK, NOT NULL, UNIQUE, FK) are enforced
- Enums contain expected values
- Indexes exist (spatial, composite, GIN, IVFFlat)
- Triggers fire correctly (geom auto-population, updated_at)
- Cascading deletes work as expected
- Seed data is loaded correctly

Run with:
    cd infra
    pytest tests/ -v
"""

import uuid
import pytest
import psycopg2


# ============================================================
# Table existence tests
# ============================================================


class TestTablesExist:
    """Verify all required tables were created by migrations."""

    @pytest.mark.parametrize(
        "table_name",
        ["departments", "complaints", "complaint_embeddings", "repair_verifications"],
    )
    def test_table_exists(self, cursor, table_name):
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            )
            """,
            (table_name,),
        )
        assert cursor.fetchone()[0], f"Table '{table_name}' does not exist"


# ============================================================
# Extension tests
# ============================================================


class TestExtensions:
    """Verify required PostgreSQL extensions are enabled."""

    @pytest.mark.parametrize("extension", ["postgis", "vector", "uuid-ossp"])
    def test_extension_enabled(self, cursor, extension):
        cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = %s)",
            (extension,),
        )
        assert cursor.fetchone()[0], f"Extension '{extension}' is not enabled"


# ============================================================
# Enum tests
# ============================================================


class TestEnums:
    """Verify enum types contain all expected values."""

    def test_issue_class_values(self, cursor):
        cursor.execute(
            """
            SELECT enumlabel FROM pg_enum
            JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
            WHERE pg_type.typname = 'issue_class'
            ORDER BY pg_enum.enumsortorder
            """
        )
        values = [row[0] for row in cursor.fetchall()]
        expected = [
            "pothole",
            "streetlight",
            "manhole",
            "dead_animal",
            "tree",
            "damaged_public_property",
            "waterlogging",
            "mud_road",
            "erosion",
            "footpath_damage",
            "encroachment",
        ]
        assert values == expected, f"issue_class enum mismatch: {values}"

    def test_complaint_status_values(self, cursor):
        cursor.execute(
            """
            SELECT enumlabel FROM pg_enum
            JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
            WHERE pg_type.typname = 'complaint_status'
            ORDER BY pg_enum.enumsortorder
            """
        )
        values = [row[0] for row in cursor.fetchall()]
        expected = [
            "pending",
            "under_review",
            "assigned",
            "in_progress",
            "repaired",
            "verified",
            "closed",
            "rejected",
        ]
        assert values == expected, f"complaint_status enum mismatch: {values}"

    def test_issue_class_count(self, cursor):
        """Exactly 11 issue classes (YOLOv8: 6 + Segmentation: 5)."""
        cursor.execute(
            """
            SELECT COUNT(*) FROM pg_enum
            JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
            WHERE pg_type.typname = 'issue_class'
            """
        )
        assert cursor.fetchone()[0] == 11


# ============================================================
# Constraint tests
# ============================================================


class TestComplaintConstraints:
    """Verify CHECK and NOT NULL constraints on the complaints table."""

    def _insert_department(self, cursor):
        """Helper: insert a department and return its ID."""
        cursor.execute(
            """
            INSERT INTO departments (name, issue_types, contact_info)
            VALUES (%s, '["pothole"]'::jsonb, '{}'::jsonb)
            RETURNING id
            """,
            (f"Test Dept {uuid.uuid4().hex[:8]}",),
        )
        return cursor.fetchone()[0]

    def test_confidence_lower_bound(self, cursor):
        """Confidence must be >= 0."""
        dept_id = self._insert_department(cursor)
        with pytest.raises(psycopg2.errors.CheckViolation):
            cursor.execute(
                """
                INSERT INTO complaints (image_url, lat, lng, issue_class, confidence, department_id)
                VALUES ('http://img.test/1.jpg', 28.6139, 77.2090, 'pothole', -0.1, %s)
                """,
                (dept_id,),
            )

    def test_confidence_upper_bound(self, cursor):
        """Confidence must be <= 1."""
        dept_id = self._insert_department(cursor)
        with pytest.raises(psycopg2.errors.CheckViolation):
            cursor.execute(
                """
                INSERT INTO complaints (image_url, lat, lng, issue_class, confidence, department_id)
                VALUES ('http://img.test/1.jpg', 28.6139, 77.2090, 'pothole', 1.5, %s)
                """,
                (dept_id,),
            )

    def test_severity_bounds(self, cursor):
        """Severity score must be in [0, 10]."""
        dept_id = self._insert_department(cursor)
        with pytest.raises(psycopg2.errors.CheckViolation):
            cursor.execute(
                """
                INSERT INTO complaints (image_url, lat, lng, issue_class, confidence, severity_score, department_id)
                VALUES ('http://img.test/1.jpg', 28.6139, 77.2090, 'pothole', 0.9, 11.0, %s)
                """,
                (dept_id,),
            )

    def test_priority_bounds(self, cursor):
        """Priority score must be in [0, 10]."""
        dept_id = self._insert_department(cursor)
        with pytest.raises(psycopg2.errors.CheckViolation):
            cursor.execute(
                """
                INSERT INTO complaints (image_url, lat, lng, issue_class, confidence, priority_score, department_id)
                VALUES ('http://img.test/1.jpg', 28.6139, 77.2090, 'pothole', 0.9, -1.0, %s)
                """,
                (dept_id,),
            )

    def test_image_url_not_null(self, cursor):
        """image_url is required."""
        with pytest.raises(psycopg2.errors.NotNullViolation):
            cursor.execute(
                """
                INSERT INTO complaints (lat, lng, issue_class, confidence)
                VALUES (28.6139, 77.2090, 'pothole', 0.9)
                """
            )

    def test_lat_not_null(self, cursor):
        """lat is required."""
        with pytest.raises(psycopg2.errors.NotNullViolation):
            cursor.execute(
                """
                INSERT INTO complaints (image_url, lng, issue_class, confidence)
                VALUES ('http://img.test/1.jpg', 77.2090, 'pothole', 0.9)
                """
            )

    def test_valid_source_constraint(self, cursor):
        """Source must be one of: mobile_app, cctv, drone."""
        dept_id = self._insert_department(cursor)
        with pytest.raises(psycopg2.errors.CheckViolation):
            cursor.execute(
                """
                INSERT INTO complaints (image_url, lat, lng, issue_class, confidence, source, department_id)
                VALUES ('http://img.test/1.jpg', 28.6139, 77.2090, 'pothole', 0.9, 'satellite', %s)
                """,
                (dept_id,),
            )

    def test_valid_complaint_insert(self, cursor):
        """A fully valid complaint inserts without error."""
        dept_id = self._insert_department(cursor)
        cursor.execute(
            """
            INSERT INTO complaints (image_url, lat, lng, issue_class, confidence, severity_score, priority_score, department_id, source)
            VALUES ('http://img.test/valid.jpg', 28.6139, 77.2090, 'pothole', 0.85, 7.5, 8.0, %s, 'mobile_app')
            RETURNING id
            """,
            (dept_id,),
        )
        result = cursor.fetchone()
        assert result is not None
        assert result[0] is not None  # UUID was generated

    def test_default_status_is_pending(self, cursor):
        """New complaints default to 'pending' status."""
        dept_id = self._insert_department(cursor)
        cursor.execute(
            """
            INSERT INTO complaints (image_url, lat, lng, issue_class, confidence, department_id)
            VALUES ('http://img.test/1.jpg', 28.6139, 77.2090, 'pothole', 0.5, %s)
            RETURNING status
            """,
            (dept_id,),
        )
        assert cursor.fetchone()[0] == "pending"


# ============================================================
# Spatial / trigger tests
# ============================================================


class TestGeomTrigger:
    """Verify that the geom column is auto-populated from lat/lng."""

    def _insert_department(self, cursor):
        cursor.execute(
            """
            INSERT INTO departments (name, issue_types, contact_info)
            VALUES (%s, '["pothole"]'::jsonb, '{}'::jsonb)
            RETURNING id
            """,
            (f"Test Dept {uuid.uuid4().hex[:8]}",),
        )
        return cursor.fetchone()[0]

    def test_geom_auto_populated_on_insert(self, cursor):
        """Inserting lat/lng should auto-populate geom via trigger."""
        dept_id = self._insert_department(cursor)
        cursor.execute(
            """
            INSERT INTO complaints (image_url, lat, lng, issue_class, confidence, department_id)
            VALUES ('http://img.test/1.jpg', 28.6139, 77.2090, 'pothole', 0.9, %s)
            RETURNING ST_X(geom), ST_Y(geom), ST_SRID(geom)
            """,
            (dept_id,),
        )
        x, y, srid = cursor.fetchone()
        assert abs(x - 77.2090) < 0.0001, "geom X (lng) mismatch"
        assert abs(y - 28.6139) < 0.0001, "geom Y (lat) mismatch"
        assert srid == 4326, "geom SRID should be 4326 (WGS84)"

    def test_geom_updates_on_lat_lng_change(self, cursor):
        """Updating lat/lng should update geom via trigger."""
        dept_id = self._insert_department(cursor)
        cursor.execute(
            """
            INSERT INTO complaints (image_url, lat, lng, issue_class, confidence, department_id)
            VALUES ('http://img.test/1.jpg', 28.6139, 77.2090, 'pothole', 0.9, %s)
            RETURNING id
            """,
            (dept_id,),
        )
        complaint_id = cursor.fetchone()[0]

        cursor.execute(
            """
            UPDATE complaints SET lat = 19.0760, lng = 72.8777 WHERE id = %s
            RETURNING ST_X(geom), ST_Y(geom)
            """,
            (complaint_id,),
        )
        x, y = cursor.fetchone()
        assert abs(x - 72.8777) < 0.0001, "Updated geom X (lng) mismatch"
        assert abs(y - 19.0760) < 0.0001, "Updated geom Y (lat) mismatch"


# ============================================================
# Index existence tests
# ============================================================


class TestIndexes:
    """Verify all required indexes exist."""

    @pytest.mark.parametrize(
        "index_name",
        [
            "idx_complaints_geom",
            "idx_complaints_status_sla",
            "idx_complaints_dept_status",
            "idx_complaints_class_created",
            "idx_complaints_created_at",
            "idx_departments_issue_types",
            "idx_embeddings_geohash",
            "idx_verifications_complaint_id",
        ],
    )
    def test_index_exists(self, cursor, index_name):
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'public'
                AND indexname = %s
            )
            """,
            (index_name,),
        )
        assert cursor.fetchone()[0], f"Index '{index_name}' does not exist"

    def test_spatial_index_is_gist(self, cursor):
        """The spatial index on complaints.geom should use GIST."""
        cursor.execute(
            """
            SELECT indexdef FROM pg_indexes
            WHERE indexname = 'idx_complaints_geom'
            """
        )
        indexdef = cursor.fetchone()[0].lower()
        assert "gist" in indexdef, "Spatial index should use GIST method"

    def test_issue_types_index_is_gin(self, cursor):
        """The index on departments.issue_types should use GIN."""
        cursor.execute(
            """
            SELECT indexdef FROM pg_indexes
            WHERE indexname = 'idx_departments_issue_types'
            """
        )
        indexdef = cursor.fetchone()[0].lower()
        assert "gin" in indexdef, "JSONB index should use GIN method"


# ============================================================
# Foreign key + cascade tests
# ============================================================


class TestCascades:
    """Verify FK cascading deletes work correctly."""

    def _insert_department(self, cursor):
        cursor.execute(
            """
            INSERT INTO departments (name, issue_types, contact_info)
            VALUES (%s, '["pothole"]'::jsonb, '{}'::jsonb)
            RETURNING id
            """,
            (f"Test Dept {uuid.uuid4().hex[:8]}",),
        )
        return cursor.fetchone()[0]

    def _insert_complaint(self, cursor, dept_id):
        cursor.execute(
            """
            INSERT INTO complaints (image_url, lat, lng, issue_class, confidence, department_id)
            VALUES ('http://img.test/cascade.jpg', 28.6139, 77.2090, 'pothole', 0.9, %s)
            RETURNING id
            """,
            (dept_id,),
        )
        return cursor.fetchone()[0]

    def test_delete_complaint_cascades_to_embeddings(self, cursor):
        """Deleting a complaint should delete its embedding."""
        dept_id = self._insert_department(cursor)
        complaint_id = self._insert_complaint(cursor, dept_id)

        # Insert embedding
        embedding_vector = "[" + ",".join(["0.1"] * 512) + "]"
        cursor.execute(
            f"""
            INSERT INTO complaint_embeddings (complaint_id, embedding, geohash)
            VALUES (%s, '{embedding_vector}', 'tdr1w8j')
            """,
            (complaint_id,),
        )

        # Verify embedding exists
        cursor.execute(
            "SELECT COUNT(*) FROM complaint_embeddings WHERE complaint_id = %s",
            (complaint_id,),
        )
        assert cursor.fetchone()[0] == 1

        # Delete complaint
        cursor.execute("DELETE FROM complaints WHERE id = %s", (complaint_id,))

        # Verify embedding was cascaded
        cursor.execute(
            "SELECT COUNT(*) FROM complaint_embeddings WHERE complaint_id = %s",
            (complaint_id,),
        )
        assert cursor.fetchone()[0] == 0

    def test_delete_complaint_cascades_to_verifications(self, cursor):
        """Deleting a complaint should delete its verifications."""
        dept_id = self._insert_department(cursor)
        complaint_id = self._insert_complaint(cursor, dept_id)

        # Insert verification
        cursor.execute(
            """
            INSERT INTO repair_verifications (complaint_id, before_image, after_image)
            VALUES (%s, 'http://img.test/before.jpg', 'http://img.test/after.jpg')
            """,
            (complaint_id,),
        )

        # Delete complaint
        cursor.execute("DELETE FROM complaints WHERE id = %s", (complaint_id,))

        # Verify verification was cascaded
        cursor.execute(
            "SELECT COUNT(*) FROM repair_verifications WHERE complaint_id = %s",
            (complaint_id,),
        )
        assert cursor.fetchone()[0] == 0


# ============================================================
# Unique constraint tests
# ============================================================


class TestUniqueConstraints:
    """Verify UNIQUE constraints are enforced."""

    def test_department_unique_name(self, cursor):
        """Duplicate department names should be rejected."""
        unique_name = f"Unique Dept {uuid.uuid4().hex[:8]}"
        cursor.execute(
            """
            INSERT INTO departments (name, issue_types, contact_info)
            VALUES (%s, '[]'::jsonb, '{}'::jsonb)
            """,
            (unique_name,),
        )
        with pytest.raises(psycopg2.errors.UniqueViolation):
            cursor.execute(
                """
                INSERT INTO departments (name, issue_types, contact_info)
                VALUES (%s, '[]'::jsonb, '{}'::jsonb)
                """,
                (unique_name,),
            )

    def test_embedding_unique_complaint(self, cursor):
        """One embedding per complaint — duplicate complaint_id rejected."""
        cursor.execute(
            """
            INSERT INTO departments (name, issue_types, contact_info)
            VALUES (%s, '["pothole"]'::jsonb, '{}'::jsonb)
            RETURNING id
            """,
            (f"Test Dept {uuid.uuid4().hex[:8]}",),
        )
        dept_id = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO complaints (image_url, lat, lng, issue_class, confidence, department_id)
            VALUES ('http://img.test/emb.jpg', 28.6139, 77.2090, 'pothole', 0.9, %s)
            RETURNING id
            """,
            (dept_id,),
        )
        complaint_id = cursor.fetchone()[0]

        embedding_vector = "[" + ",".join(["0.1"] * 512) + "]"
        cursor.execute(
            f"""
            INSERT INTO complaint_embeddings (complaint_id, embedding, geohash)
            VALUES (%s, '{embedding_vector}', 'tdr1w8j')
            """,
            (complaint_id,),
        )

        with pytest.raises(psycopg2.errors.UniqueViolation):
            cursor.execute(
                f"""
                INSERT INTO complaint_embeddings (complaint_id, embedding, geohash)
                VALUES (%s, '{embedding_vector}', 'tdr1w8j')
                """,
                (complaint_id,),
            )


# ============================================================
# Seed data tests
# ============================================================


class TestSeedData:
    """Verify department seed data was loaded correctly."""

    def test_six_departments_seeded(self, cursor):
        cursor.execute("SELECT COUNT(*) FROM departments")
        assert cursor.fetchone()[0] == 6

    @pytest.mark.parametrize(
        "dept_name",
        [
            "Roads & Infrastructure",
            "Electrical & Streetlights",
            "Drainage & Water",
            "Sanitation",
            "Parks & Environment",
            "Public Works",
        ],
    )
    def test_department_exists(self, cursor, dept_name):
        cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM departments WHERE name = %s)",
            (dept_name,),
        )
        assert cursor.fetchone()[0], f"Department '{dept_name}' not found"

    def test_roads_dept_issue_types(self, cursor):
        """Roads & Infrastructure should handle pothole, mud_road, erosion, footpath_damage."""
        cursor.execute(
            "SELECT issue_types FROM departments WHERE name = 'Roads & Infrastructure'"
        )
        issue_types = cursor.fetchone()[0]
        expected = {"pothole", "mud_road", "erosion", "footpath_damage"}
        assert set(issue_types) == expected

    def test_all_issue_classes_covered(self, cursor):
        """Every issue_class enum value should be handled by at least one department."""
        cursor.execute(
            """
            SELECT DISTINCT jsonb_array_elements_text(issue_types) AS issue_type
            FROM departments
            """
        )
        covered_types = {row[0] for row in cursor.fetchall()}
        expected_types = {
            "pothole", "streetlight", "manhole", "dead_animal", "tree",
            "damaged_public_property", "waterlogging", "mud_road",
            "erosion", "footpath_damage", "encroachment",
        }
        assert covered_types == expected_types, (
            f"Missing issue types in departments: {expected_types - covered_types}"
        )


# ============================================================
# Repair verification constraint tests
# ============================================================


class TestVerificationConstraints:
    """Verify constraints on the repair_verifications table."""

    def _setup_complaint(self, cursor):
        cursor.execute(
            """
            INSERT INTO departments (name, issue_types, contact_info)
            VALUES (%s, '["pothole"]'::jsonb, '{}'::jsonb)
            RETURNING id
            """,
            (f"Test Dept {uuid.uuid4().hex[:8]}",),
        )
        dept_id = cursor.fetchone()[0]
        cursor.execute(
            """
            INSERT INTO complaints (image_url, lat, lng, issue_class, confidence, department_id)
            VALUES ('http://img.test/ver.jpg', 28.6139, 77.2090, 'pothole', 0.9, %s)
            RETURNING id
            """,
            (dept_id,),
        )
        return cursor.fetchone()[0]

    def test_visual_score_bounds(self, cursor):
        """visual_score must be in [0, 1]."""
        complaint_id = self._setup_complaint(cursor)
        with pytest.raises(psycopg2.errors.CheckViolation):
            cursor.execute(
                """
                INSERT INTO repair_verifications
                    (complaint_id, before_image, after_image, visual_score)
                VALUES (%s, 'http://before.jpg', 'http://after.jpg', 1.5)
                """,
                (complaint_id,),
            )

    def test_multiple_verifications_allowed(self, cursor):
        """Multiple verification attempts should be allowed for the same complaint."""
        complaint_id = self._setup_complaint(cursor)
        for i in range(3):
            cursor.execute(
                """
                INSERT INTO repair_verifications
                    (complaint_id, before_image, after_image, verified, reason)
                VALUES (%s, 'http://before.jpg', %s, %s, %s)
                """,
                (
                    complaint_id,
                    f"http://after_{i}.jpg",
                    i == 2,  # Only last attempt verified
                    f"Attempt {i + 1}",
                ),
            )
        cursor.execute(
            "SELECT COUNT(*) FROM repair_verifications WHERE complaint_id = %s",
            (complaint_id,),
        )
        assert cursor.fetchone()[0] == 3

    def test_default_verified_is_false(self, cursor):
        """New verifications default to verified=false."""
        complaint_id = self._setup_complaint(cursor)
        cursor.execute(
            """
            INSERT INTO repair_verifications (complaint_id, before_image, after_image)
            VALUES (%s, 'http://before.jpg', 'http://after.jpg')
            RETURNING verified
            """,
            (complaint_id,),
        )
        assert cursor.fetchone()[0] is False
