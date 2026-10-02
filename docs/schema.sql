-- =====================================================================
-- La base de datos mamalona para crear polidrive
-- =====================================================================
CREATE DATABASE IF NOT EXISTS polidrive
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE polidrive;

CREATE TABLE usuarios (
    id           BIGINT       NOT NULL AUTO_INCREMENT,
    email        VARCHAR(190) NOT NULL,
    nombre       VARCHAR(150) NOT NULL,
    password     VARCHAR(128) NOT NULL,
    last_login   DATETIME(6)  NULL,
    is_superuser TINYINT(1)   NOT NULL DEFAULT 0,
    is_staff     TINYINT(1)   NOT NULL DEFAULT 0,
    is_active    TINYINT(1)   NOT NULL DEFAULT 1,
    date_joined  DATETIME(6)  NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_usuarios_email (email)
) ENGINE=InnoDB;

CREATE TABLE carpetas (
    id         BIGINT       NOT NULL AUTO_INCREMENT,
    name       VARCHAR(255) NOT NULL,
    owner_id   BIGINT       NOT NULL,
    parent_id  BIGINT       NULL,
    created_at DATETIME(6)  NOT NULL,
    eliminado  TINYINT(1)   NOT NULL DEFAULT 0,   -- si esta en 1 esta en la papelera
    trash_at   DATETIME(6)  NULL,                 -- cuando ya se envio
    PRIMARY KEY (id),
    KEY idx_carpetas_owner  (owner_id),
    KEY idx_carpetas_parent (parent_id),
    CONSTRAINT fk_carpetas_owner  FOREIGN KEY (owner_id)  REFERENCES usuarios (id) ON DELETE CASCADE,
    CONSTRAINT fk_carpetas_parent FOREIGN KEY (parent_id) REFERENCES carpetas (id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- archivos  nomas guarda la key, nose pq no me deja guardar el binario
CREATE TABLE archivos (
    id        BIGINT          NOT NULL AUTO_INCREMENT,
    name      VARCHAR(255)    NOT NULL,           -- nombre visible para el usuario
    owner_id  BIGINT          NOT NULL,
    folder_id BIGINT          NULL,               -- NULL = raíz
    upload    VARCHAR(500)    NOT NULL,           -- key en S3: usuario_<id>/<uuid>_<nombre>
    size      BIGINT UNSIGNED NOT NULL DEFAULT 0,
    upl_at    DATETIME(6)     NOT NULL,
    eliminado TINYINT(1)      NOT NULL DEFAULT 0,
    trash_at  DATETIME(6)     NULL,
    PRIMARY KEY (id),
    KEY idx_archivos_owner  (owner_id),
    KEY idx_archivos_folder (folder_id),
    CONSTRAINT fk_archivos_owner  FOREIGN KEY (owner_id)  REFERENCES usuarios (id) ON DELETE CASCADE,
    CONSTRAINT fk_archivos_folder FOREIGN KEY (folder_id) REFERENCES carpetas (id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- archivos_compartidos  (muchos a muchos usuario <-> archivo, con permiso)
CREATE TABLE archivos_compartidos (
    id           BIGINT      NOT NULL AUTO_INCREMENT,
    file_id      BIGINT      NOT NULL,
    shr_by_id    BIGINT      NOT NULL,             -- quien comparte (el dueño)
    shr_with_id  BIGINT      NOT NULL,             -- con quien se comparte
    perm         VARCHAR(10) NOT NULL DEFAULT 'view',   -- 'view' (lectura) | 'edit' (escritura)
    created_at   DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_arch_comp (file_id, shr_with_id),
    CONSTRAINT fk_comp_file FOREIGN KEY (file_id)     REFERENCES archivos (id) ON DELETE CASCADE,
    CONSTRAINT fk_comp_by   FOREIGN KEY (shr_by_id)   REFERENCES usuarios (id) ON DELETE CASCADE,
    CONSTRAINT fk_comp_with FOREIGN KEY (shr_with_id) REFERENCES usuarios (id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- enlaces_publicos  (tabla aparte: permite historial de enlaces revocados)
CREATE TABLE enlaces_publicos (
    id            BIGINT      NOT NULL AUTO_INCREMENT,
    file_id       BIGINT      NOT NULL,
    token         VARCHAR(64) NOT NULL,
    created_by_id BIGINT      NOT NULL,
    created_at    DATETIME(6) NOT NULL,
    active        TINYINT(1)  NOT NULL DEFAULT 1,
    revoked_at    DATETIME(6) NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_enlace_token (token),
    CONSTRAINT fk_enl_file FOREIGN KEY (file_id)       REFERENCES archivos (id) ON DELETE CASCADE,
    CONSTRAINT fk_enl_by   FOREIGN KEY (created_by_id) REFERENCES usuarios (id) ON DELETE CASCADE
) ENGINE=InnoDB;