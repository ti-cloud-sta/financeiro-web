CREATE TABLE turnover_planos_saude (
    idTurnoverPlano INT AUTO_INCREMENT PRIMARY KEY,
    idColaborador INT NOT NULL,
    idEmpresa INT NOT NULL,
    idImportacao INT NOT NULL,
    competencia VARCHAR(7) NULL,
    valor DECIMAL(10, 2) NULL,
    resolvido CHAR(1) DEFAULT 'N',
    createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (idColaborador) REFERENCES colaboradores(idColaborador),
    FOREIGN KEY (idEmpresa) REFERENCES empresas(idEmpresas),
    FOREIGN KEY (idImportacao) REFERENCES importacoes(idImportacoes)
);
