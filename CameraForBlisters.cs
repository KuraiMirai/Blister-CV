using System;
using System.Collections;
using System.Diagnostics;
using System.IO;
using UnityEngine;
using Debug = UnityEngine.Debug;

[RequireComponent(typeof(Collider))]
public class BlisterPhotoCapture : MonoBehaviour
{
    [Header("Camera Settings")]
    public Camera targetCamera;
    public int resolutionWidth = 1280;
    public int resolutionHeight = 720;
    [SerializeField] private float capturePrecision = 0.001f;

    [Header("Trigger Settings")]
    public string blisterTag = "Blister";

    [Header("Python Integration")]
    public string pythonScriptPath = @"C:/Users/Mirai/Desktop/KURSACH/PythonCode/KodRabotayet3.py";
    public string pythonExePath = "C:/Users/Mirai/AppData/Local/Programs/Python/Python313/python.exe";
    public float processingTimeout = 5f;

    [Header("Saving Settings")]
    public string saveFolder = @"C:\Users\Mirai\Desktop\KURSACH\Photos";
    public string fileNamePrefix = "Blister_";

    private Transform currentBlister;
    private bool isProcessing;

    // Класс для десериализации JSON
    [System.Serializable]
    private class PythonResult
    {
        public bool has_defects;
        public int defect_count;
        public string blister_id;
        public string status;
    }

    private void Start()
    {
        if (targetCamera == null) targetCamera = Camera.main;
        Directory.CreateDirectory(saveFolder);
    }

    private void OnTriggerStay(Collider other)
    {
        if (!other.CompareTag(blisterTag)) return;

        float distance = Vector3.Distance(other.transform.position, transform.position);
        if (distance <= capturePrecision && !isProcessing)
        {
            currentBlister = other.transform;
            StartCoroutine(CaptureAndProcess());
        }
    }

    private IEnumerator CaptureAndProcess()
    {
        isProcessing = true;

        // 1. Захват фото
        string photoPath = Path.Combine(saveFolder, $"{fileNamePrefix}{DateTime.Now:yyyyMMdd_HHmmssfff}.png");
        yield return StartCoroutine(CaptureCenterPhoto(photoPath));
        Debug.Log($"Фото сохранено: {photoPath}");

        // 2. Запуск Python
        ProcessStartInfo psi = new ProcessStartInfo
        {
            FileName = pythonExePath,
            Arguments = $"\"{pythonScriptPath}\" --image \"{photoPath}\"",
            UseShellExecute = false,
            RedirectStandardOutput = true,
            CreateNoWindow = true,
            StandardOutputEncoding = System.Text.Encoding.UTF8 // Важно для кириллицы
        };

        Debug.Log($"Запуск Python: {psi.FileName} {psi.Arguments}");

        using (Process process = Process.Start(psi))
        {
            yield return new WaitUntil(() => process.HasExited);
            string output = process.StandardOutput.ReadToEnd().Trim();
            Debug.Log($"Raw Python output: {output}");

            if (currentBlister != null)
            {
                try
                {
                    PythonResult result = JsonUtility.FromJson<PythonResult>(output);
                    bool hasDefects = result.has_defects;
                    currentBlister.GetComponent<ConveyorMovement>()?.SetDefectStatus(hasDefects);
                    Debug.Log($"Defect status parsed: {hasDefects} (Count: {result.defect_count})");
                }
                catch (Exception ex)
                {
                    Debug.LogError($"JSON parse error: {ex.Message}");
                    currentBlister.GetComponent<ConveyorMovement>()?.SetDefectStatus(false);
                }
            }
        }

        isProcessing = false;
    }

    private IEnumerator CaptureCenterPhoto(string path)
    {
        yield return new WaitForEndOfFrame();

        RenderTexture rt = new RenderTexture(resolutionWidth, resolutionHeight, 24);
        targetCamera.targetTexture = rt;
        Texture2D photo = new Texture2D(resolutionWidth, resolutionHeight, TextureFormat.RGB24, false);

        targetCamera.Render();
        yield return null;
        targetCamera.Render();

        RenderTexture.active = rt;
        photo.ReadPixels(new Rect(0, 0, resolutionWidth, resolutionHeight), 0, 0);
        photo.Apply();

        File.WriteAllBytes(path, photo.EncodeToPNG());

        targetCamera.targetTexture = null;
        RenderTexture.active = null;
        Destroy(rt);
        Destroy(photo);
    }

    private void OnDrawGizmos()
    {
        Gizmos.color = Color.green;
        Gizmos.DrawWireSphere(transform.position, capturePrecision);
    }
}