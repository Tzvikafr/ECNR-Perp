function metrics_export_csv(records, outPath)
%METRICS_EXPORT_CSV Save metrics table to CSV.

if isempty(records)
    error('metrics_export_csv:Empty', 'No records to export.');
end

T = struct2table(records);
writetable(T, outPath);
end
