namespace BlindReviewSample;

public sealed class BlindSyncService
{
    public string BuildLookupKey(SoilRecord soil)
    {
        return soil.SampleSoiGlobalId ?? string.Empty;
    }

    public string? ResolveCoordinateKey(SoilRecord soil)
    {
        if (!string.IsNullOrWhiteSpace(soil.Twd97XMap) && !string.IsNullOrWhiteSpace(soil.Twd97YMap))
        {
            return $"{soil.Twd97XMap},{soil.Twd97YMap}";
        }

        if (!string.IsNullOrWhiteSpace(soil.Twd97XUser) && !string.IsNullOrWhiteSpace(soil.Twd97YUser))
        {
            return $"{soil.Twd97XUser},{soil.Twd97YUser}";
        }

        if (!string.IsNullOrWhiteSpace(soil.Wgs84Long) && !string.IsNullOrWhiteSpace(soil.Wgs84Lat))
        {
            return $"{soil.Wgs84Long},{soil.Wgs84Lat}";
        }

        return null;
    }

    public CollectioRecord? MatchCollectio(SoilRecord soil, IEnumerable<CollectioRecord> rows)
    {
        return rows.FirstOrDefault(row => row.UniqueRowId == soil.ParentRowId);
    }

    public bool ShouldRecalculateLand(string? currentCounty, string? currentTown2, SoilRecord incoming)
    {
        return currentCounty != incoming.County || currentTown2 != incoming.Town2;
    }

    public ResultFeature BuildGeneralUpdate(SoilRecord soil, ResultFeature existing)
    {
        ResultFeature result = new ResultFeature
        {
            SampleSoiGlobalId = existing.SampleSoiGlobalId,
            Geometry = existing.Geometry
        };

        foreach (var attribute in existing.Attributes)
        {
            result.Attributes[attribute.Key] = attribute.Value;
        }

        result.Attributes["land_process_log"] = soil.LandProcessLog;

        return result;
    }
}
