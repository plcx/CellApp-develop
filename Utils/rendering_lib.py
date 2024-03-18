import vtk
import numpy as np
import nibabel as nib
import os

def nib_load(file_name):
    assert os.path.isfile(file_name), "File {} not exist".format(file_name)
    return nib.load(file_name).get_fdata()

def create_vtk_image_data(label_array):
    # Create a VTK image data from the labeled numpy array
    vtk_image = vtk.vtkImageData()
    vtk_image.SetDimensions(label_array.shape)
    vtk_image.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)

    for i in range(label_array.shape[0]):
        for j in range(label_array.shape[1]):
            for k in range(label_array.shape[2]):
                vtk_image.SetScalarComponentFromDouble(i, j, k, 0, label_array[i, j, k])

    return vtk_image

def render_and_export_obj(input_file, output_path):
    label_array = nib_load(input_file)
    # Convert the labeled numpy array to VTK image data
    vtk_image_data = create_vtk_image_data(label_array)
    # Initialize renderer, render window, and interactor
    ren = vtk.vtkRenderer()
    renWin = vtk.vtkRenderWindow()
    renWin.AddRenderer(ren)
    renWin.SetOffScreenRendering(1)
    iren = vtk.vtkRenderWindowInteractor()
    iren.SetRenderWindow(renWin)

    # Iterate through unique labels and extract surfaces
    labels = np.unique(label_array)
    for i, label in enumerate(labels):
        if label == 0:
            continue  # Skip background

        # Extract surface using vtkDiscreteMarchingCubes
        surf = vtk.vtkDiscreteMarchingCubes()
        surf.SetInputData(vtk_image_data)
        surf.SetValue(0, label)
        surf.Update()

        # smoothing the mesh
        smoother = vtk.vtkWindowedSincPolyDataFilter()
        if vtk.VTK_MAJOR_VERSION <= 5:
            smoother.SetInput(surf.GetOutput())
        else:
            smoother.SetInputConnection(surf.GetOutputPort())

        # increase this integer set number of iterations if smoother surface wanted
        smoother.SetNumberOfIterations(80)
        smoother.NonManifoldSmoothingOn()
        smoother.NormalizeCoordinatesOn()  # The positions can be translated and scaled such that they fit within a range of [-1, 1] prior to the smoothing computation
        smoother.GenerateErrorScalarsOn()
        smoother.Update()



        # Map the smoothed surface to an actor and set its color
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(smoother.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(np.random.rand(), np.random.rand(), np.random.rand())

        # Add actor to the renderer
        ren.AddActor(actor)

    # Set background color and reset camera
    ren.SetBackground(0.1, 0.1, 0.1)
    ren.ResetCamera()

    # Export the scene to an OBJ file
    obj_exporter = vtk.vtkOBJExporter()
    obj_exporter.SetInput(renWin)
    obj_exporter.SetFilePrefix(output_path)
    obj_exporter.Write()

    # Start the render window interactor
    iren.Initialize()
    renWin.Render()




